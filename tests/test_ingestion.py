from pathlib import Path
from app.ingestion.pdf import load_and_split_pdf

def test_sample_pdf_extracts_page_text_and_metadata():
    fixture = Path(__file__).parent / "fixtures" / "research_basics.pdf"
    chunks = load_and_split_pdf(fixture)
    assert chunks
    assert "LangGraph" in chunks[0].page_content
    assert chunks[0].metadata["page"] == 0
    assert chunks[0].metadata["total_pages"] == 1
