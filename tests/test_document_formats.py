from pathlib import Path
from docx import Document as WordDocument

from app.ingestion.document import extract_document, load_and_split_document


def test_txt_document_is_extracted_and_split(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("This research note explains evidence-based document retrieval. " * 20, encoding="utf-8")
    chunks = load_and_split_document(path)
    assert chunks
    assert "evidence-based" in chunks[0].page_content
    assert chunks[0].metadata["section"] == "Text document"


def test_docx_document_paragraphs_and_tables_are_extracted(tmp_path):
    path = tmp_path / "paper.docx"
    document = WordDocument()
    document.add_paragraph("ResearchFlow document evidence")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Finding"
    table.cell(0, 1).text = "Strong evidence"
    document.save(path)

    extracted = extract_document(path)
    assert len(extracted) == 1
    assert "ResearchFlow document evidence" in extracted[0].page_content
    assert "Strong evidence" in extracted[0].page_content
