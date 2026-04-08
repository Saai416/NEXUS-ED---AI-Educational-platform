

import os
from dotenv import load_dotenv

load_dotenv()
import sys
import json
import logging
import asyncio
import hashlib
from typing import TypedDict, Optional, List, Dict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import openai

# --- Improvement Modules ---
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import redis

# --- Setup Imports ---
# Add parent directory to sys.path to allow importing KG2 and Querysolver
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# --- Import KG2 (Graph Search) ---
# KG2.py is imported directly. It contains `ask_graph(question)`
try:
    import KG2
except ImportError:
    logging.warning("Could not import KG2. Ensure it is in the parent directory.")
    KG2 = None

# --- Import Querysolver Components (Vector Search) ---
# Since Querysolver.py is a script and may not be safe to import without side effects,
# we replicate the necessary Pinecone/OpenAI logic here using the keys from the original file.
from pinecone.grpc import PineconeGRPC as Pinecone
import uuid

# --- Configurations ---
# Keys extracted from Querysolver.py
PINECONE_KEY = os.getenv("PINECONE_KEY", "")
PINECONE_HOST = os.getenv("PINECONE_HOST", "https://rag-index-xfor3af.svc.aped-4627-b74a.pinecone.io")
OPENAI_MODEL_EMBEDDING = "text-embedding-ada-002"
OPENAI_MODEL_CHAT = "gpt-4o-mini"

# Initialize Clients
openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=PINECONE_KEY)

# Redis Configuration (Try connecting, fall back to simple dict memory cache if failed)
# In production, use os.getenv("REDIS_URL")
try:
    cache_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    cache_client.ping() # Check connection
    print("--- [Cache] Connected to Redis ---")
except Exception:
    print("--- [Cache] Redis not available, using in-memory dictionary ---")
    class SimpleCache:
        def __init__(self): self.store = {}
        def get(self, key): return self.store.get(key)
        def set(self, key, value, ex=None): self.store[key] = value
        def exists(self, key): return key in self.store
    cache_client = SimpleCache()

# Connect to the index
try:
    vector_index = pc.Index(host=PINECONE_HOST)
except Exception as e:
    logging.error(f"Failed to connect to Pinecone index: {e}")
    vector_index = None

# --- Helper: Caching Decorator ---
def get_cache_key(prefix: str, data: str) -> str:
    """Generate a consistent cache key."""
    hash_object = hashlib.md5(data.encode())
    return f"{prefix}:{hash_object.hexdigest()}"

# --- 1. Define State ---
class AgentState(TypedDict):
    """
    The state of the agent in the LangGraph workflow.
    """
    question: str
    namespace: Optional[str]  # Namespace for vector search
    vector_results: Annotated[Optional[List[str]], lambda x, y: y]
    graph_results: Annotated[Optional[Dict], lambda x, y: y]
    final_answer: Optional[str]

# --- 2. Define Nodes (Async & Robust) ---

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception))
async def retrieve_vector(state: AgentState) -> AgentState:
    """
    Node to retrieve information from the Vector Database (Pinecone).
    Async, Retries on failure, Caches results.
    """
    question = state["question"]
    namespace = state.get("namespace", "Default")
    
    # Check Cache
    cache_key = get_cache_key(f"vector_search:{namespace}", question)
    cached = cache_client.get(cache_key)
    if cached:
        print(f"--- [Vector Node] Cache Hit for '{question}' ---")
        return {"vector_results": json.loads(cached)}

    print(f"--- [Vector Node] Searching for: '{question}' in namespace '{namespace}' ---")

    if not vector_index:
        return {"vector_results": []}

    try:
        # Create embedding (async call if available, otherwise runs in thread)
        client = openai.AsyncClient()
        response = await client.embeddings.create(
            input=question,
            model=OPENAI_MODEL_EMBEDDING
        )
        embedding = response.data[0].embedding

        # Query Pinecone (Pinecone GRPC can be used synchronously, wrapper needed for true async or just assume threaded IO)
        # Note: Pinecone python client is sync by default usually. We'll run it directly as it's IO bound.
        vector_result = vector_index.query(
            namespace=namespace,
            vector=embedding,
            top_k=10,  # Increased from 3 to 10 for better retrieval
            include_values=False,
            include_metadata=True
        )

        results = []
        for item in vector_result.matches:
            if 'metadata' in item and 'text' in item['metadata']:
                results.append(item['metadata']['text'])
        
        # Set Cache
        cache_client.set(cache_key, json.dumps(results), ex=3600) # 1 hour expire
        print(f"--- [Vector Node] Found {len(results)} matches ---")
        return {"vector_results": results}
        
    except Exception as e:
        print(f"--- [Vector Node] Error: {e} ---")
        # Re-raise for tenacity to handle retry
        raise e

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception))
async def retrieve_graph(state: AgentState) -> AgentState:
    """
    Node to retrieve information from the Knowledge Graph (Neo4j).
    Async wrapper for KG2, Retries on failure, Caches results.
    """
    question = state["question"]
    
    # Check Cache
    cache_key = get_cache_key("graph_search", question)
    cached = cache_client.get(cache_key)
    if cached:
        print(f"--- [Graph Node] Cache Hit for '{question}' ---")
        # We stored the whole dict
        return {"graph_results": json.loads(cached)}

    print(f"--- [Graph Node] Searching for: '{question}' ---")

    if not KG2:
        print("--- [Graph Node] KG2 module not available ---")
        return {"graph_results": None}

    try:
        # KG2.ask_graph is blocking/sync. Run in executor to avoid blocking the loop.
        loop = asyncio.get_running_loop()
        # partial used to pass arguments
        from functools import partial
        out = await loop.run_in_executor(None, partial(KG2.ask_graph, question))
        
        if out.get("error"):
             print(f"--- [Graph Node] Error from KG2: {out['error']} ---")
             return {"graph_results": None}
        else:
             # Cache result
             cache_client.set(cache_key, json.dumps(out), ex=3600)
             print("--- [Graph Node] Search successful ---")
             return {"graph_results": out}

    except Exception as e:
        print(f"--- [Graph Node] Exception: {e} ---")
        raise e

async def synthesize_answer(state: AgentState) -> AgentState:
    """
    Node to synthesize the final answer using results from both sources.
    Handles partial results: displays Pinecone if Neo4j fails, Neo4j if Pinecone fails, or combines both.
    """
    print("--- [Synthesize Node] Generating final answer ---")
    
    question = state["question"]
    vector_docs = state.get("vector_results", [])
    graph_data = state.get("graph_results", {})
    
    graph_answer = None
    if graph_data and graph_data.get("nl_answer"):
        graph_answer = graph_data["nl_answer"]

    # Check what sources have results
    has_vector = bool(vector_docs)
    has_graph = bool(graph_answer)
    
    # Construct context string based on available sources
    context_parts = []
    
    if has_vector:
        context_parts.append("VECTOR SEARCH RESULTS:\n" + "\n".join(f"- {doc}" for doc in vector_docs))
    
    if has_graph:
        context_parts.append(f"KNOWLEDGE GRAPH ANSWER: {graph_answer}")
    
    # If neither source has results, return a helpful message
    if not has_vector and not has_graph:
        print("--- [Synthesize Node] No results from either source ---")
        state["final_answer"] = "I don't know."
        return state
    
    full_context = "\n\n".join(context_parts)

    # Generate answer using LLM with improved prompt
    llm = ChatOpenAI(model=OPENAI_MODEL_CHAT, temperature=0)
    
    # Determine which sources provided data for better prompt
    if has_vector and has_graph:
        source_instruction = "Both vector search and knowledge graph provided information. Combine them comprehensively to give a complete answer."
    elif has_vector:
        source_instruction = "Only vector search provided information. Use it to answer the question."
    else:  # has_graph only
        source_instruction = "Only the knowledge graph provided information. Use it to answer the question."
    
    prompt = (
        f"You are a helpful assistant. Answer the user question based on the provided context.\n"
        f"{source_instruction}\n"
        f"Be concise but comprehensive. If the context doesn't fully answer the question, provide what information is available.\n\n"
        f"Context:\n{full_context}\n\n"
        f"Question: {question}"
    )

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    state["final_answer"] = response.content
    
    print(f"--- [Synthesize Node] Answer generated from: {'Vector' if has_vector else ''}{' + ' if has_vector and has_graph else ''}{'Graph' if has_graph else ''} ---")
    
    return state

# --- 3. Build Graph (Parallel Execution) ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("vector_search", retrieve_vector)
workflow.add_node("graph_search", retrieve_graph)
workflow.add_node("combiner", synthesize_answer)

# Add Edges
# Flow: Start -> Parallel(Vector, Graph) -> Combiner -> End
workflow.set_entry_point("vector_search") # We start with a fan-out
# Actually, to fan-out, we need a common start node or just add edge from START?
# LangGraph: To run in parallel, current step transitions to multiple nodes.
# Let's use a dummy start node or just handle the entry better.
# Easier pattern: Start -> "dispatcher" -> [Vector, Graph] -> Combiner
# Or simply:
# workflow.set_entry_point("dispatcher") ...
# But StateGraph entry point is single node.
# We can make a simple passthrough node "start".

async def start_node(state: AgentState):
    return state

workflow.add_node("start", start_node)
workflow.set_entry_point("start")
workflow.add_edge("start", "vector_search")
workflow.add_edge("start", "graph_search")
workflow.add_edge("vector_search", "combiner")
workflow.add_edge("graph_search", "combiner")
workflow.add_edge("combiner", END)

# Compile
app = workflow.compile()

# --- Entry Point for testing ---
if __name__ == "__main__":
    # Example usage
    async def main():
        user_input = "Tell me about the Odyssey project and its dependencies."
        namespace_input = "TestContent" 

        print(f"Starting workflow with question: {user_input}")
        
        inputs = {"question": user_input, "namespace": namespace_input}
        
        # Async invocation
        result = await app.ainvoke(inputs)
        
        print("\n=== FINAL ANSWER ===")
        print(result["final_answer"])

    asyncio.run(main())
