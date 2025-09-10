# pdf-toc-service
add table of contents to bundled pdf
cat > README.md <<'MD'
# pdf-toc-service

Flask API that inserts a **hyperlinked Table of Contents** into a PDF using **PyMuPDF (fitz)**, optionally updating PDF bookmarks/outlines. Designed to run in **GitHub Codespaces** and callable from **Power Automate**.

---

## Files

- `function_app.py` (or `app.py`) — Flask app
- `requirements.txt` — dependencies:
  ```
