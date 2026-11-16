from functools import lru_cache
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_chroma import Chroma
from app.core.config import CHROMA_DIR

class LocalChromaEmbeddings:
    """Lightweight local ONNX embeddings bundled with Chroma; no paid API or PyTorch."""
    def __init__(self):
        self.function = DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.function(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.function([text])[0]

@lru_cache(maxsize=1)
def get_embeddings():
    return LocalChromaEmbeddings()

def get_vector_store():
    return Chroma(
        collection_name="researchflow_documents",
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )
