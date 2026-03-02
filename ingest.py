import os
import fitz  # PyMuPDF
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
import time

# ─── Configuration ───────────────────────────────────────────────
GUIDELINES_PATH = "./guidelines"
CHROMA_DB_PATH = "./chroma_db"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

# Condition mapping — folder name to collection name
CONDITION_MAP = {
    "hypertension": "hypertension_guidelines",
    "diabetes": "diabetes_guidelines",
    "cholesterol": "cholesterol_guidelines"
}

# ─── Initialize ChromaDB ─────────────────────────────────────────
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# ─── Embedding Function via Ollama ───────────────────────────────
embedding_function = OllamaEmbeddingFunction(
    url=f"{OLLAMA_URL}/api/embeddings",
    model_name=EMBED_MODEL,
    timeout=300
)

# ─── PDF Text Extraction ─────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text

# ─── Semantic Chunking ───────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 200, overlap: int = 20) -> list:
    """
    Split text into overlapping chunks.
    chunk_size: number of words per chunk
    overlap: number of words to overlap between chunks
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks

# ─── Ingest One PDF ──────────────────────────────────────────────
def ingest_pdf(pdf_path: str, condition: str, collection):
    """Extract, chunk, and store one PDF into ChromaDB."""
    filename = os.path.basename(pdf_path)
    print(f"  Processing: {filename}")

    # Extract text
    text = extract_text_from_pdf(pdf_path)

    if not text.strip():
        print(f"  WARNING: No text extracted from {filename}. Skipping.")
        return

    # Chunk the text
    chunks = chunk_text(text)
    print(f"  Generated {len(chunks)} chunks")

    # Prepare data for ChromaDB
    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{filename}_chunk_{i}"
        documents.append(chunk)
        metadatas.append({
            "source": filename,
            "condition": condition,
            "chunk_index": i
        })
        ids.append(chunk_id)

    # Store in ChromaDB in small batches to avoid timeout
    batch_size = 2
    total = len(documents)
    for i in range(0, total, batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        collection.add(
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids
        )
        print(f"  Stored batch {i//batch_size + 1}/{(total+batch_size-1)//batch_size}")
        time.sleep(2)  # small delay to avoid overwhelming Ollama
    print(f"  Done: {total} chunks stored in ChromaDB")

# ─── Main Ingestion Pipeline ─────────────────────────────────────
def run_ingestion():
    """Process all PDFs in the guidelines folder and store in ChromaDB."""
    print("=" * 50)
    print("Starting Medical Guidelines Ingestion")
    print("=" * 50)

    total_chunks = 0

    for folder_name, collection_name in CONDITION_MAP.items():
        folder_path = os.path.join(GUIDELINES_PATH, folder_name)

        if not os.path.exists(folder_path):
            print(f"\nWARNING: Folder not found — {folder_path}")
            continue

        # Get or create ChromaDB collection for this condition
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )

        # Skip if already has data
        if collection.count() > 0:
            print(f"  Already ingested — skipping ({collection.count()} chunks exist)")
            continue

        print(f"\nProcessing condition: {folder_name.upper()}")
        print(f"Collection: {collection_name}")

        # Find all PDFs in this folder
        pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

        if not pdf_files:
            print(f"  No PDF files found in {folder_path}")
            continue

        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            ingest_pdf(pdf_path, folder_name, collection)
            total_chunks += collection.count()

    print("\n" + "=" * 50)
    print(f"Ingestion Complete!")
    print(f"Collections created: {list(CONDITION_MAP.values())}")
    print("=" * 50)

# ─── Verify ChromaDB Contents ────────────────────────────────────
def verify_ingestion():
    """Print a summary of what's stored in ChromaDB."""
    print("\nVerifying ChromaDB contents...")
    for collection_name in CONDITION_MAP.values():
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
            count = collection.count()
            print(f"  {collection_name}: {count} chunks stored")
        except Exception as e:
            print(f"  {collection_name}: Not found — {e}")

if __name__ == "__main__":
    run_ingestion()
    verify_ingestion()
