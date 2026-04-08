import os
import sys
from pinecone.grpc import PineconeGRPC as Pinecone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Config
PINECONE_KEY = 'pcsk_6HzKZU_LH1rZYEMrANNDYYoc11UBkwPGWhYCZVckNGmo4Z2uPBbBoGDpCknPmosnJuYnnM'
PINECONE_HOST = 'https://rag-index-xfor3af.svc.aped-4627-b74a.pinecone.io'
OPENAI_MODEL_EMBEDDING = "text-embedding-ada-002"

# Init
pc = Pinecone(api_key=PINECONE_KEY)
index = pc.Index(host=PINECONE_HOST)
client = OpenAI()

def test_query(query, namespace="Default"):
    print(f"\n--- Testing Query: '{query}' (Namespace: {namespace}) ---")
    
    # Embed
    resp = client.embeddings.create(input=query, model=OPENAI_MODEL_EMBEDDING)
    embedding = resp.data[0].embedding
    
    # Search
    results = index.query(
        namespace=namespace,
        vector=embedding,
        top_k=5,
        include_values=False,
        include_metadata=True
    )
    
    print(f"Found {len(results.matches)} matches.")
    for mock in results.matches:
        print(f"[{mock.score:.4f}] {mock.metadata.get('text', '')[:100]}...")

if __name__ == "__main__":
    # Test the failing query
    # Note: User might be using a specific namespace if they selected one in the UI.
    # The default in integrated_app.py is "Default". 
    # If the user uploaded to "Topic1" and searches in "Topic1", we need to know.
    # We will try "Default" and maybe iterate topics.
    
    test_query("What are the lab facilities in northeastern university?", namespace="NEU")
    
    # Test the working query
    test_query("What are the lab facilities in northeastern university? give response from pinecone and neo4j separately", namespace="NEU")
