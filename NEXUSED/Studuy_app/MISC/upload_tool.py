import os
from dotenv import load_dotenv

load_dotenv()
import json
import uuid
import itertools
import requests
import re
import time
import logging

import streamlit as st
from openai import OpenAI
import nltk
from bs4 import BeautifulSoup

# --- External Service Imports ---
try:
    from pinecone.grpc import PineconeGRPC as Pinecone
except ImportError:
    st.error("Pinecone library not found. Please install pinecone-client[grpc].")

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import CypherSyntaxError
except ImportError:
    st.error("Neo4j driver not found. Please install neo4j.")

# --- NLTK Setup ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

# --- Configuration & Secrets ---
# Ideally, these should be in st.secrets or environment variables.
# Using values provided in original files for compatibility.

# OpenAI
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "") # Ensure env var is set if possible
client = OpenAI()

# Pinecone
PINECONE_KEY = 'pcsk_6HzKZU_LH1rZYEMrANNDYYoc11UBkwPGWhYCZVckNGmo4Z2uPBbBoGDpCknPmosnJuYnnM'
PINECONE_HOST = 'https://rag-index-xfor3af.svc.aped-4627-b74a.pinecone.io'
EMBEDDING_MODEL = "text-embedding-ada-002"

# Neo4j
NEO4J_URI = "neo4j+s://ba74b87c.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "RIjZjP4J7SNOFNlpnaDw_boP5i50OpL5-d1E6ZNOhe4"


# ==========================================
# 1. Pinecone / Vector DB Logic (Adapted from Querysolver.py)
# ==========================================

def init_pinecone():
    """Initialize Pinecone connection."""
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(host=PINECONE_HOST)
    return index

def get_content_from_url(url):
    """Scrape and tokenize content from a URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        sentences = nltk.sent_tokenize(text)
        return sentences, text # Return both list of sentences and full text
    except Exception as e:
        st.error(f"Error fetching URL: {e}")
        return [], ""

def upsert_to_pinecone(index, sentences, namespace):
    """Generate embeddings and upsert to Pinecone."""
    if not sentences:
        return
    
    st.write(f"Generating embeddings for {len(sentences)} sentences...")
    
    # 1. Generate Embeddings
    try:
        response = client.embeddings.create(
            input=sentences,
            model=EMBEDDING_MODEL
        )
    except Exception as e:
        st.error(f"Error generating embeddings: {e}")
        return

    # 2. Prepare Vectors
    vectors = []
    for sentence, embedding_item in zip(sentences, response.data):
        vectors.append({
            'id': str(uuid.uuid4()),
            'values': embedding_item.embedding,
            'metadata': {
                'text': sentence
            }
        })
    
    # 3. Upsert in Batches
    def chunks(iterable, batch_size=100):
        it = iter(iterable)
        chunk = tuple(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))

    st.write("Upserting to Pinecone...")
    count = 0
    for chunk in chunks(vectors, batch_size=100):
        index.upsert(vectors=chunk, namespace=namespace)
        count += len(chunk)
    
    st.success(f"Successfully upserted {count} vectors to namespace '{namespace}'.")


# ==========================================
# 2. Neo4j / Knowledge Graph Logic (Adapted from KG2.py)
# ==========================================

def extract_entities_and_relations(text: str) -> dict:
    """
    Uses OpenAI to extract knowledge graph data (Nodes & Edges) from text.
    """
    if not text.strip():
        return None

    system_prompt = (
        "You are an expert at extracting entities and relationships from text. "
        "Your goal is to create a knowledge graph. "
        "Extract the entities and relationships from the provided text and format them as a list of nodes and a list of edges."
    )
    
    # Using function calling as in KG2.py
    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_knowledge_graph",
                "description": "Creates a knowledge graph from a list of nodes and edges.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "label": {"type": "string"},
                                    "properties": {"type": "object"}
                                },
                                "required": ["id", "label"]
                            }
                        },
                        "edges": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {"type": "string"},
                                    "target": {"type": "string"},
                                    "label": {"type": "string"},
                                    "properties": {"type": "object"}
                                },
                                "required": ["source", "target", "label"]
                            }
                        }
                    },
                    "required": ["nodes", "edges"]
                }
            }
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract entities and relationships from the following text: \n\n{text[:15000]}"} # Limit text size to avoid token limits
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "create_knowledge_graph"}}
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        graph_data = json.loads(tool_call.function.arguments)

        # Normalize IDs (snake_case) - Important for consistency
        def normalize_id(s):
            if not s: return s
            return re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_')

        for node in graph_data.get("nodes", []):
            node['id'] = normalize_id(node['id'])
        
        for edge in graph_data.get("edges", []):
            edge['source'] = normalize_id(edge['source'])
            edge['target'] = normalize_id(edge['target'])
            
        return graph_data

    except Exception as e:
        st.error(f"Error extracting entities: {e}")
        return None

def load_graph_to_neo4j(graph_data: dict):
    """
    Loads the extracted graph data into Neo4j.
    """
    if not graph_data:
        return

    st.write("Connecting to Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    node_labels = {node['id']: node['label'] for node in graph_data.get("nodes", [])}

    with driver.session() as session:
        # 1. Create Nodes
        for node in graph_data.get("nodes", []):
            try:
                cypher_query = f"MERGE (n:`{node['label']}` {{id: $id}}) SET n += $properties"
                session.run(cypher_query, id=node['id'], properties=node.get('properties', {}))
            except Exception as e:
                st.warning(f"Failed to merge node {node['id']}: {e}")

        # 2. Create Edges
        for edge in graph_data.get("edges", []):
            try:
                source_label = node_labels.get(edge['source'])
                target_label = node_labels.get(edge['target'])
                
                if not source_label or not target_label:
                    continue # Skip if we can't fully qualify the node

                cypher_query = (
                    f"MATCH (source:`{source_label}` {{id: $source_id}}) "
                    f"MATCH (target:`{target_label}` {{id: $target_id}}) "
                    f"MERGE (source)-[r:`{edge['label']}`]->(target) "
                    f"SET r += $properties"
                )
                session.run(cypher_query, 
                            source_id=edge['source'], 
                            target_id=edge['target'], 
                            properties=edge.get('properties', {}))
            except Exception as e:
                st.warning(f"Failed to merge edge {edge['source']}->{edge['target']}: {e}")

    driver.close()
    st.success("Successfully loaded Knowledge Graph data to Neo4j.")


# ==========================================
# 3. Main Streamlit App
# ==========================================

def app():
    # Removed st.set_page_config as it will be called in the main app
    
    st.title("Teacher Content Upload Portal")
    st.markdown("Use this tool to upload educational content. The system will automatically:\n"
                "1. **Vectorize** the text for search (Pinecone).\n"
                "2. **Extract Knowledge Graph** entities and relationships (Neo4j).")

    # --- Sidebar Inputs ---
    with st.sidebar:
        st.header("Configuration")
        content_name = st.text_input("Content/Topic Name (Namespace)", value="General")
        input_method = st.radio("Input Method", ["Manual Text", "URL"])

    # --- Main Content Area ---
    raw_text = ""
    sentences = []

    if input_method == "Manual Text":
        raw_text = st.text_area("Paste content here:", height=300)
        if raw_text:
            sentences = nltk.sent_tokenize(raw_text)
    else:
        url = st.text_input("Enter Content URL:")
        if url:
            if st.button("Fetch URL Content"):
                with st.spinner("Fetching..."):
                    sentences, raw_text = get_content_from_url(url)
                    if raw_text:
                        st.text_area("Preview Fetched Text:", value=raw_text[:1000]+"...", height=200)

    # --- Process Button ---
    if st.button("Upload & Process Content", type="primary"):
        if not raw_text:
            st.error("Please provide some text content first.")
            return
        
        if not content_name:
            st.error("Please specify a Content Name (Namespace).")
            return

        st.markdown("---")
        col1, col2 = st.columns(2)

        # 1. Processing Pinecone
        with col1:
            st.subheader("1. Vector Database (Pinecone)")
            with st.spinner("Processing vectors..."):
                try:
                    index = init_pinecone()
                    upsert_to_pinecone(index, sentences, content_name)
                except Exception as e:
                    st.error(f"Pinecone Error: {e}")

        # 2. Processing Neo4j
        with col2:
            st.subheader("2. Knowledge Graph (Neo4j)")
            with st.spinner("Extracting & Loading Graph..."):
                try:
                    graph_data = extract_entities_and_relations(raw_text)
                    if graph_data:
                        st.json(graph_data, expanded=False) # Show preview of what was extracted
                        load_graph_to_neo4j(graph_data)
                    else:
                        st.warning("No entities extracted from text.")
                except Exception as e:
                    st.error(f"Neo4j Error: {e}")

        st.success("All processing complete!")
        save_topic(content_name)

def save_topic(topic_name):
    """Save the topic name to a local registry."""
    try:
        if os.path.exists("topics.json"):
            with open("topics.json", "r") as f:
                topics = json.load(f)
        else:
            topics = []
        
        if topic_name not in topics:
            topics.append(topic_name)
            with open("topics.json", "w") as f:
                json.dump(topics, f)
            st.info(f"Topic '{topic_name}' registered for students.")
    except Exception as e:
        st.warning(f"Could not save topic to registry: {e}")

if __name__ == "__main__":
    app()
