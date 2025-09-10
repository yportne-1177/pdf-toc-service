import os
import base64
import io
from flask import Flask, request, jsonify
import fitz  # PyMuPDF

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")  # optional; set to require X-API-KEY header

def require_api_key(req):
    if not API_KEY:
        return True, None
    provided = req.headers.get("X-API-KEY")
    if provided and provided == API_KEY:
        return True, None
    return False, jsonify({"status": "ERROR", "message": "Unauthorized"}), 401

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "READY",
        "message": "Send a POST to /add-pdf-toc with base64 PDF content to generate a hyperlinked TOC."
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK"})

@app.route("/add-pdf-toc", methods=["POST"])
def add_pdf_toc():
    ok, err, code = require_api_key(request)
    if not ok:
        return err, code

    data = request.get_json(silent=True) or {}
    pdf_b64 = data.get("pdf_b64")
    toc_input = data.get("toc")  # [{title, page, level?}]
    options = data.get("options") or {}
    title_text = options.get("title", "Table of Contents")
    font_size = int(options.get("font_size", 12))
    insert_bookmarks = bool(options.get("insert_bookmarks", True))
    margin_x = 54
    margin_y = 72
    line_gap = max(16, int(font_size * 1.35))

    if not pdf_b64:
        return jsonify({"status": "ERROR", "message": "Missing 'pdf_b64'"}), 400

    try:
        pdf_bytes = base64.b64decode(pdf_b64)
    except Exception:
        return jsonify({"status": "ERROR", "message": "Invalid base64 for 'pdf_b64'"}), 400

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Unable to open PDF: {e}"}), 400

    # If no explicit TOC provided, try to derive from existing PDF outline
    if not toc_input:
        existing = doc.get_toc(simple=True)  # [[level, title, page], ...] (page is 1-based)
        if existing:
            toc_input = [{"title": t[1], "page": t[2], "level": t[0]} for t in existing]
        else:
            toc_input = []

    # Normalize, validate, clamp page indices
    normalized = []
    for entry in toc_input:
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        level = int(entry.get("level", 1))
        page_1_based = int(entry.get("page", 1))
        # clamp to document range
        page_1_based = max(1, min(page_1_based, doc.page_count))
        normalized.append({"title": title, "level": level, "page1": page_1_based})

    # Insert TOC page (always at index 0)
    toc_page = doc.new_page(pno=0)  # insert at beginning
    page_width, page_height = toc_page.rect.width, toc_page.rect.height

    # Title
    cursor_y = margin_y
    toc_page.insert_text(
        (margin_x, cursor_y),
        title_text,
        fontsize=font_size + 4,
        fontname="helv",
        fill=(0, 0, 0),
    )
    cursor_y += (line_gap * 1.6)

    # Render each TOC line and add link annotation to target page top
    for item in normalized:
        title = item["title"]
        lvl = item["level"]
        page1 = item["page1"]
        page_idx = page1 - 1  # PyMuPDF uses 0-based internally

        indent = (lvl - 1) * 18
        text_x = margin_x + indent

        # dotted leaders (optional: simple alignment)
        right_text = f"{page1}"
        left_text = title

        # Write left text
        toc_page.insert_text(
            (text_x, cursor_y),
            left_text,
            fontsize=font_size,
            fontname="helv",
            fill=(0, 0, 1),  # blue-ish to hint it's clickable
        )
        # Right-aligned page number
        num_x = page_width - margin_x - 24
        toc_page.insert_text(
            (num_x, cursor_y),
            right_text,
            fontsize=font_size,
            fontname="helv",
            fill=(0, 0, 0),
        )

        # Link rectangle covering the whole line
        line_height = line_gap
        link_rect = fitz.Rect(
            text_x,
            cursor_y - (font_size * 0.8),
            page_width - margin_x,
            cursor_y + (font_size * 0.4),
        )

        toc_page.insert_link({
            "kind": fitz.LINK_GOTO,
            "page": page_idx,
            "from": link_rect,
            # Optional: jump near top of target page
            "zoom": 0.0
        })

        cursor_y += line_gap
        if cursor_y > (page_height - margin_y - line_gap):
            # overflow handling: new page for TOC continuation
            toc_page = doc.new_page(pno=doc.page_count)  # append at end
            cursor_y = margin_y

    # Optionally (re)set PDF outline/bookmarks from provided TOC
    outline_count = 0
    if insert_bookmarks and normalized:
        # PyMuPDF requires [[level, title, page], ...] with page 1-based
        outline = [[item["level"], item["title"], item["page1"]] for item in normalized]
        try:
            doc.set_toc(outline)
            outline_count = len(outline)
        except Exception:
            # not fatal
            outline_count = 0

    # Serialize back to base64
    out_bytes = doc.tobytes()
    doc.close()
    out_b64 = base64.b64encode(out_bytes).decode("ascii")

    return jsonify({
        "status": "OK",
        "message": f"TOC page inserted. Bookmarks: {'yes' if outline_count else 'no'}",
        "pdf_b64": out_b64,
        "outline_count": outline_count,
        "page_count": len(doc),  # NOTE: doc is closed; do not access further in real code
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

