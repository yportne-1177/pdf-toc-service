from flask import Flask, request, jsonify
import fitz, base64

app = Flask(__name__)

@app.route("/add-pdf-toc", methods=["GET", "POST"])
def add_pdf_toc():
    if request.method == "GET":
        return jsonify({
            "status": "READY",
            "message": "Send a POST request with base64 PDF content to generate a hyperlinked TOC."
        })

    try:
        data = request.get_json()
        pdf_b64 = data["fileContent"]
        title = data.get("title", "Hyperlinked Table of Contents")
        zoom = float(data.get("zoom", 1.0))

        pdf_bytes = base64.b64decode(pdf_b64)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        toc = doc.get_toc(simple=False) or [[lvl, t, p, {}] for (lvl, t, p) in doc.get_toc()]
        if not toc:
            return jsonify({"status": "ERROR", "error": "No bookmarks found"}), 400

        # Insert TOC pages
        LEFT, RIGHT, TOP = 54, 54, 54
        LINE_H, FS = 18, 11
        FONT, COLOR = "helv", (0, 0, 1)
        first_rect = doc[0].rect
        lines_per = max(1, int(((first_rect.height - 2 * TOP)//LINE_H) - 2))
        num_toc_pages = (len(toc) + lines_per - 1)//lines_per

        for _ in range(num_toc_pages):
            doc.new_page(pno=0)

        page_index = 0
        cur = doc[page_index]
        y = TOP
        cur.insert_text((LEFT, y), title, fontsize=16, fontname=FONT, fill=(0,0,0))
        y += 2*LINE_H

        for (lvl, title_i, p1, _meta) in toc:
            if y > cur.rect.height - TOP:
                page_index += 1
                cur = doc[page_index]
                y = TOP
                cur.insert_text((LEFT, y), f"{title} (cont.)", fontsize=14, fontname=FONT, fill=(0,0,0))
                y += 2*LINE_H
            x = LEFT + max(0, (int(lvl)-1))*14
            label = (title_i or "").strip()
            if len(label) > 180:
                label = label[:179] + "…"
            cur.insert_text((x, y), label, fontsize=FS, fontname=FONT, fill=COLOR)
            pn = str(int(p1))
            est = len(pn) * FS * 0.5
            cur.insert_text((cur.rect.width - RIGHT - est, y), pn, fontsize=FS, fontname=FONT, fill=(0,0,0))
            clickable_rect = fitz.Rect(x, y - FS, cur.rect.width - RIGHT, y + 4)
            target_idx = max(0, min((int(p1) - 1) + num_toc_pages, doc.page_count - 1))
            cur.insert_link({"kind": fitz.LINK_GOTO, "from": clickable_rect, "page": target_idx, "zoom": zoom})
            y += LINE_H

        out_bytes = doc.tobytes()
        doc.close()
        return jsonify({"status": "OK", "fileContent": base64.b64encode(out_bytes).decode("ascii")})
    except Exception as e:
        return jsonify({"status": "ERROR", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

