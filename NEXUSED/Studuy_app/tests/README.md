# Test Scripts

This folder contains all test, debug, and diagnostic scripts for the Study App project.

## Test Scripts

### `test_query_fixes.py`
Tests the query retrieval fixes for handling vague queries.
- Tests vector search and knowledge graph integration
- Validates partial result handling
- Verifies synonym expansion and broad pattern matching

**Usage:**
```powershell
cd c:\Studuy_app
python tests\test_query_fixes.py
```

### `test_kg_retrieval.py`
Tests knowledge graph retrieval functionality.

### `test_auth_flow.py`
Tests authentication and authorization flows.

---

## Debug Scripts

### `debug_retrieval.py`
Debugging script for retrieval issues in the RAG system.

### `diagnose_neo4j.py`
Diagnostic tool for Neo4j connection and query issues.

### `inspect_graph.py`
Inspects the knowledge graph structure and contents.

---

## Verification Scripts

### `verify_upload.py`
Verifies that content uploads to Pinecone and Neo4j are working correctly.

### `reproduce_issue.py`
Script to reproduce specific issues for debugging purposes.

---

## Running Tests

To run all tests:
```powershell
cd c:\Studuy_app
python -m pytest tests/
```

To run a specific test:
```powershell
python tests\test_query_fixes.py
```

---

## Notes

- All scripts assume they are run from the project root directory (`c:\Studuy_app`)
- Make sure all dependencies are installed before running tests
- Some tests may require active connections to Pinecone and Neo4j
