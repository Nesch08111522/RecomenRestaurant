import sys
import os
from pathlib import Path

out_dir = Path(r"C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant\.work\extracted")
out_dir.mkdir(parents=True, exist_ok=True)

docs = {
    "preguntas.docx": r"C:\Users\Nancy Sandoval\.dsh\attachments\v1\files\b4\b47d5ef54bd0e5c528eb206ec6e9a9770567a9ff9c69cff10625981057edcf44\PREGUNTAS QUE TIENES QUE RESPONDER.docx",
    "apf2.pdf": r"C:\Users\Nancy Sandoval\.dsh\attachments\v1\files\ba\bab9e747b6d887dbc0e7210a41c6975a9bfeb80bf9087c7049873c04d6c41f32\SmartResto_APF2_Informe_Integrado Original.pdf",
    "avance3.pdf": r"C:\Users\Nancy Sandoval\.dsh\attachments\v1\files\47\4789a1a07cc8f16fd6943e09c48c9086ea74e5bd2205dd6aeccbbb4368aacc84\AVANCE DE PROYECTO FINAL 3 (1).pdf",
    "rubrica.pdf": r"C:\Users\Nancy Sandoval\.dsh\attachments\v1\files\9e\9e9becbc3eb337019435f47e5682b9ab6224b5307807e54f0653ddd46fc1c367\RUBRICA PROYECTO AV3 (1).pdf",
}

def extract_docx(path):
    import docx
    d = docx.Document(path)
    parts = []
    for p in d.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    for ti, t in enumerate(d.tables):
        parts.append(f"\n[Tabla {ti+1}]")
        for r in t.rows:
            parts.append(" | ".join(c.text.strip() for c in r.cells))
    return "\n".join(parts)

def extract_pdf(path):
    from pypdf import PdfReader
    r = PdfReader(path)
    parts = []
    for i, page in enumerate(r.pages):
        parts.append(f"\n===== PAGINA {i+1} =====\n")
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:
            parts.append(f"[error extract page {i+1}: {e}]")
    return "\n".join(parts)

for name, path in docs.items():
    try:
        if name.endswith(".docx"):
            txt = extract_docx(path)
        else:
            txt = extract_pdf(path)
        out = out_dir / (name.replace(".docx", ".txt").replace(".pdf", ".txt"))
        out.write_text(txt, encoding="utf-8")
        print(f"OK {name} -> {out} ({len(txt)} chars)")
    except Exception as e:
        print(f"FAIL {name}: {e!r}")
