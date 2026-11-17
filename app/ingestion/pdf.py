from app.ingestion.document import load_and_split_document


def load_and_split_pdf(path):
    """Backward-compatible PDF ingestion entry point."""
    return load_and_split_document(path)
