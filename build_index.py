# 1_build_index.py
import faiss
import numpy as np
import pickle
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")
genai.configure(api_key=api_key)

# --- Configuration ---
FILE_PATHS = ['data/modul-linux.txt']
INDEX_PATH = "index/my_faiss_index.index"
DOCS_PATH = "index/documents.pkl"
EMBEDDING_MODEL = 'models/text-embedding-004'

# Configure your API key
# genai.configure(api_key="YOUR_API_KEY")

def embed_documents(documents: list[str]) -> np.ndarray:
    """Embeds the documents using the configured model."""
    print(f"⏳ Embedding {len(documents)} document chunks...")
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=documents,
            task_type="RETRIEVAL_DOCUMENT",
            title="RAG Documents"
        )
        print("✅ Documents embedded successfully.")
        return np.array(result['embedding'])
    except Exception as e:
        print(f"An error occurred during embedding: {e}")
        raise

def build_and_save_index(documents: list[str], embeddings: np.ndarray):
    """Builds and saves the FAISS index and the documents."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Create the 'index' directory if it doesn't exist
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)

    # Save the FAISS index
    faiss.write_index(index, INDEX_PATH)
    print(f"✅ FAISS index with {index.ntotal} vectors saved to {INDEX_PATH}")

    # Save the document chunks using pickle
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(documents, f)
    print(f"✅ Document chunks saved to {DOCS_PATH}")

def main():
    """Main function to process documents and build the index."""
    all_chunked_documents = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for path in FILE_PATHS:
        try:
            # Note: This example reads a .txt file. You'll need a library
            # like PyMuPDF (fitz) to read text from a PDF.
            # Example for a text file:
            with open(path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            
            if full_text.strip():
                print(f"✅ Successfully read {path}")
                chunks = text_splitter.split_text(full_text)
                all_chunked_documents.extend(chunks)
                print(f"📄 Split '{path}' into {len(chunks)} chunks.")
            else:
                print(f"⚠️ Warning: The file '{path}' is empty.")
        except FileNotFoundError:
            print(f"❌ Error: The file '{path}' was not found.")
        except Exception as e:
            print(f"An error occurred while processing {path}: {e}")

    if all_chunked_documents:
        document_embeddings = embed_documents(all_chunked_documents)
        build_and_save_index(all_chunked_documents, document_embeddings)
    else:
        print("\n❌ No content was processed. Index was not created.")

if __name__ == "__main__":
    main()