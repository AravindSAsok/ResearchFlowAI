import shutil
import subprocess
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from docx import Document as WordDocument

from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_document(path: str | Path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        return [Document(page_content=text, metadata={"section": "Text document"})]
    if suffix == ".docx":
        word = WordDocument(str(path))
        paragraphs = [p.text.strip() for p in word.paragraphs if p.text.strip()]
        tables = [" | ".join(cell.text.strip() for cell in row.cells) for table in word.tables for row in table.rows]
        text = "\n".join(paragraphs + tables)
        if not text.strip():
            raise ValueError("No readable text was found in this Word document.")
        return [Document(page_content=text, metadata={"section": "Word document"})]
    if suffix == ".doc":
        antiword = shutil.which("antiword")
        if antiword:
            result = subprocess.run([antiword, str(path)], capture_output=True, text=True, timeout=30, check=True)
            text = result.stdout
        else:
            try:
                import pythoncom
                from win32com.client import DispatchEx
            except ImportError as exc:
                raise ValueError("Legacy .doc extraction requires Microsoft Word automation (pywin32) or Antiword. Save as .docx if neither is available.") from exc
            pythoncom.CoInitialize()
            word = None
            document = None
            try:
                word = DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = 0
                word.AutomationSecurity = 3
                word.Options.UpdateLinksAtOpen = False
                document = word.Documents.Open(str(path.resolve()), False, True, False)
                text = document.Content.Text
            finally:
                if document is not None:
                    document.Close(False)
                if word is not None:
                    word.Quit()
                pythoncom.CoUninitialize()
        if not text.strip():
            raise ValueError("No readable text was found in this Word document.")
        return [Document(page_content=text, metadata={"section": "Word document"})]
    raise ValueError("Supported formats: PDF, DOC, DOCX and TXT.")


def load_and_split_document(path: str | Path):
    pages = extract_document(path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    return splitter.split_documents(pages)


def load_and_split_pdf(path: str | Path):
    return load_and_split_document(path)
