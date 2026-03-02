from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
import os

# ─── Configuration ───────────────────────────────────────────────
CHROMA_DB_PATH = "./chroma_db"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
MIN_SIMILARITY_SCORE = 0.7
TOP_K_RESULTS = 2

CONDITION_COLLECTION_MAP = {
    "hypertension": "hypertension_guidelines",
    "diabetes": "diabetes_guidelines",
    "cholesterol": "cholesterol_guidelines",
    "high blood pressure": "hypertension_guidelines",
    "high glucose": "diabetes_guidelines",
    "high cholesterol": "cholesterol_guidelines",
}

# ─── Initialize ChromaDB and Embedding Function ──────────────────
embedding_function = OllamaEmbeddingFunction(
    url=f"{OLLAMA_URL}/api/embeddings",
    model_name=EMBED_MODEL,
    timeout=300
)

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# ─── Input Schema ────────────────────────────────────────────────
class GuidelineRAGToolInput(BaseModel):
    """Input schema for GuidelineRAGTool."""
    query: str = Field(
        ...,
        description="The medical condition or question to search guidelines for. Example: 'treatment for high blood pressure 155/95'"
    )
    condition: str = Field(
        ...,
        description="The specific condition to search. Must be one of: hypertension, diabetes, cholesterol, high blood pressure, high glucose, high cholesterol"
    )

# ─── RAG Tool ────────────────────────────────────────────────────
class GuidelineRAGTool(BaseTool):
    name: str = "Medical Guideline Retriever"
    description: str = (
        "Searches and retrieves relevant evidence-based medical guidelines "
        "from WHO and NIH documents stored in the knowledge base. "
        "Use this tool when you need clinical guidelines for hypertension, "
        "diabetes, or cholesterol management. "
        "Input should be a specific medical query and condition name."
    )
    args_schema: Type[BaseModel] = GuidelineRAGToolInput

    def _run(self, query: str, condition: str) -> str:
        try:
            # Map condition to collection name
            condition_lower = condition.lower().strip()
            collection_name = CONDITION_COLLECTION_MAP.get(condition_lower)

            if not collection_name:
                return f"No guideline collection found for condition: {condition}. Available conditions: hypertension, diabetes, cholesterol."

            # Get the collection
            try:
                collection = client.get_collection(
                    name=collection_name,
                    embedding_function=embedding_function
                )
            except Exception:
                return f"Collection '{collection_name}' not found. Please run ingest.py first."

            # Query ChromaDB
            results = collection.query(
                query_texts=[query],
                n_results=TOP_K_RESULTS,
                include=["documents", "metadatas", "distances"]
            )

            # Check if results are empty
            if not results["documents"] or not results["documents"][0]:
                return f"No relevant guidelines found for: {query}"

            # Process and format results
            retrieved_chunks = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                # Convert distance to similarity score
                similarity = 1 - distance

                # Filter by minimum similarity threshold
                if similarity < MIN_SIMILARITY_SCORE:
                    continue
                
                # Limit chunk text to first 300 words to avoid overwhelming LLM
                doc_trimmed = " ".join(doc.split()[:300])
                retrieved_chunks.append(
                f"[Source: {metadata.get('source', 'Unknown')} | "
                f"Similarity: {similarity:.2f}]\n{doc_trimmed}"
            )

                # Log similarity score
                print(f"  [RAG] Retrieved chunk {i+1} — similarity: {similarity:.2f} from {metadata.get('source', 'Unknown')}")

            if not retrieved_chunks:
                return f"No guidelines found above similarity threshold ({MIN_SIMILARITY_SCORE}) for: {query}"

            # Return formatted results
            formatted_output = f"Retrieved {len(retrieved_chunks)} relevant guideline(s) for '{query}':\n\n"
            formatted_output += "\n\n---\n\n".join(retrieved_chunks)

            return formatted_output

        except Exception as e:
            return f"Error retrieving guidelines: {str(e)}"