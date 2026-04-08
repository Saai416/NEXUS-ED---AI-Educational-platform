# Integrated Application Documentation

## Overview
The `integrated_app.py` consolidates two distinct search paradigms—Vector Search (via Pinecone) and Knowledge Graph Search (via Neo4j)—into a single, high-performance workflow using **LangGraph**.

The application is designed to be **robust**, **fast**, and **comprehensive**, combining results from both sources to answer user queries.

## Modules & Technologies

The following key modules are utilized in the application:

### Core Framework
-   **`langgraph`**: Orchestrates the workflow, managing state and node transitions.
-   **`langchain`**: Provides the interface for LLM interactions (GPT-4) and embeddings.
-   **`asyncio`**: Enables **parallel execution** of search tasks, significantly reducing latency.

### Intelligence & Search
-   **`openai`**: Powering `gpt-4o` for answer synthesis and `text-embedding-ada-002` for vectorization.
-   **`pinecone-client`**: Handles high-speed vector retrieval.
-   **`neo4j`**: Manages complex relationship queries in the Knowledge Graph.

### Performance & Reliability
-   **`tenacity`**: Provides **automatic retries** with exponential backoff for all external API calls, ensuring the app doesn't crash on transient network errors.
-   **`redis`**: Implements **caching**. Results for identical queries are served instantly from the cache (Redis or in-memory fallback), bypassing expensive API calls.

## System Architecture

### The Workflow
The application follows a **parallel execution pattern**:

1.  **Entry Point**: The system receives a user query.
2.  **Dispatcher**: The workflow immediately branches into two concurrent tasks.
3.  **Parallel Tasks**:
    -   **Vector Search**: Converts the query to an embedding and searches Pinecone for similar text chunks.
    -   **Graph Search**: Converts the query to Cypher (via `KG2.py` logic) and queries Neo4j for structured relationships.
    *Note: These run simultaneously. The total time depends only on the slowest task, not the sum of both.*
4.  **Combiner (Synthesizer)**:
    -   Waits for both tasks to complete.
    -   Aggregates the context.
    -   Uses GPT-4 to synthesize a final natural language answer, resolving conflicts or combining details from both sources.

### Flowchart

```mermaid
graph TD
    Start([Start]) --> Dispatcher{Dispatcher}
    
    subgraph "Parallel Execution"
        Dispatcher -->|Async| Vector[Retrieve Vector<br/>(Pinecone + Redis Cache)]
        Dispatcher -->|Async| Graph[Retrieve Graph<br/>(Neo4j + Redis Cache)]
    end
    
    Vector --> Combiner[Synthesize Answer<br/>(GPT-4 Aggregation)]
    Graph --> Combiner
    
    Combiner --> End([End])
    
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef async fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,stroke-dasharray: 5 5;
    class Vector,Graph async;
```

## How It Works (Internal Logic)

1.  **State Management**: A `TypedDict` keeps track of the `question`, `vector_results`, `graph_results`, and `final_answer`.
2.  **Caching Strategy**: Before any API call, the system checks Redis using a hash of the query. If found, it returns immediately.
3.  **Error Handling**: If Neo4j or Pinecone fails even after retries, the node returns `None` (empty) instead of crashing, allowing the other source to still provide an answer.
