from typing import List
import chromadb
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# ---- Initialize global Chroma client & collection ----
chroma_client = chromadb.Client()

collection = chroma_client.get_or_create_collection(
    name="pdf_chunks",
    embedding_function=embedding_fn
)

# ---- Step 1: Extract PDF text ----
def extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# ---- Step 2: Chunk text ----
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

# ---- Step 3: Store chunks in Chroma ----
def index_pdf(file_path: str, doc_id: str):
    text = extract_pdf_text(file_path)
    chunks = chunk_text(text)

    # Store each chunk
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk],
            ids=[f"{doc_id}_{i}"],
            metadatas=[{"doc_id": doc_id}]
        )
    return len(chunks)

# ---- Step 4: Retrieve relevant chunks ----
def retrieve_chunks(query: str, k: int = 3) -> List[str]:
    results = collection.query(
        query_texts=[query],
        n_results=k
    )
    return results["documents"][0]
