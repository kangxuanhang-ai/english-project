from io import BytesIO
from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

ALLOWED_MIMES = {
    ".txt": {"text/plain"},
    ".md": {"text/plain", "text/markdown", "text/x-markdown", "application/octet-stream"},
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}


def validate_upload(filename: str, content_type: str | None, file_size: int, max_size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("不支持的文件扩展名")
    if file_size > max_size:
        raise ValueError("文件大小超过限制")
    mime = (content_type or "application/octet-stream").split(";")[0].strip().lower()
    allowed = ALLOWED_MIMES.get(ext, set())
    if mime not in allowed:
        raise ValueError("MIME 类型不匹配")
    return ext


def default_title(filename: str) -> str:
    return Path(filename).stem[:200] or filename[:200]


def parse_document(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md"):
        return raw.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        import fitz

        doc = fitz.open(stream=raw, filetype="pdf")
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
    if ext == ".docx":
        from docx import Document

        doc = Document(BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError("不支持的文件格式")
