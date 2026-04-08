
import os
import sys
import asyncio
import json

# Ensure we can import KG2
sys.path.append(os.getcwd())

try:
    import KG2
except ImportError:
    print("Error: Could not import KG2.py")
    sys.exit(1)

def test_retrieval():
    print("--- Testing Graph Retrieval ---")
    
    # Check for API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not found in environment variables.")
        print("The script might fail if the key is typically loaded from .env or elsewhere.")
    
    questions = [
        "Who is Vinith?",
        "What is Artificial Intelligence?",
        "Where does Vinith plan to study?"
    ]
    
    for q in questions:
        print(f"\nQuestion: {q}")
        try:
            result = KG2.ask_graph(q)
            if result.get("error"):
                 print(f"Error: {result['error']}")
                 if result.get("cypher"):
                     print(f"Generated Cypher: {result['cypher']}")
            else:
                 print(f"Cypher: {result.get('cypher')}")
                 print(f"Answer: {result.get('nl_answer')}")
                 print(f"Raw Results: {json.dumps(result.get('results'), indent=2)}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    test_retrieval()
