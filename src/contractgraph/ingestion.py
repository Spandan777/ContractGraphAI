from pathlib import Path
from pypdf import PdfReader
import io

def extract_text(source):
    if isinstance(source, str):
        return source
    if isinstance(source, Path):
        if source.suffix.lower() == ".pdf":
            return "\n".join(p.extract_text() or "" for p in PdfReader(str(source)).pages)
        return source.read_text(encoding="utf-8", errors="replace")
    name = getattr(source, "name", "")
    data = source.getvalue() if hasattr(source, "getvalue") else source.read()
    if str(name).lower().endswith(".pdf"):
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)

def validate_document(text):
    issues = []
    if not isinstance(text, str) or not text.strip(): issues.append("Document is empty.")
    elif len(text.strip()) < 80: issues.append("Document is very short; results may be unreliable.")
    return {"valid": isinstance(text, str) and bool(text.strip()), "issues": issues,
            "characters": len(text) if isinstance(text, str) else 0}
