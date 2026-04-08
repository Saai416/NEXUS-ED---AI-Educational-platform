import json
import os
from dotenv import load_dotenv

load_dotenv()
import openai
from neo4j import GraphDatabase
import re
import time

# --- 1. OpenAI Configuration ---
# Reads the API key from an environment variable named "OPENAI_API_KEY".
# The script will fail if this environment variable is not set.
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- 2. Neo4j Configuration ---
# Reads your Neo4j credentials from environment variables.
NEO4J_URI="neo4j+s://ba74b87c.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="RIjZjP4J7SNOFNlpnaDw_boP5i50OpL5-d1E6ZNOhe4"

def extract_entities_and_relations(text: str) -> dict:
    """
    Uses OpenAI's function calling to extract entities and relationships from text.
    Implements chunking to handle larger documents.
    """
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    print("Extracting entities and relations from text...")
    
    # 1. Chunking Logic
    CHUNK_SIZE = 4000
    OVERLAP = 200
    chunks = []
    
    # Simple character-based chunking
    if len(text) <= CHUNK_SIZE:
        chunks = [text]
    else:
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunks.append(text[start:end])
            start += CHUNK_SIZE - OVERLAP
            
    aggregated_nodes = {} # Keyed by ID to deduplicate
    aggregated_edges = []
    
    print(f"--- Processing {len(chunks)} text chunks ---")

    for i, chunk in enumerate(chunks):
        print(f"Analyzing chunk {i+1}/{len(chunks)}...")
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert at extracting entities and relationships for a Knowledge Graph. "
                            "1. ENTITY IDs: Use the PRECISE, CANONICAL entity name as the 'id'. Do NOT use integers or generic IDs like '1' or 'Entity'.\n"
                            "   - Example: For 'Northeastern University', id='Northeastern_University'. "
                            "   - Consistency: If an entity appears as 'Northeastern' and 'Northeastern University', use the longer, more specific name as the ID for both.\n"
                            "2. FIRST PERSON RESOLUTION: If the text uses 'I', 'me', 'my', or 'myself', YOU MUST extract this as a Node with id='Vinith' and label='Person' (or 'Student' if appropriate).\n"
                            "   - Do NOT create a node with id='I'.\n"
                            "3. PROPERTIES: Extract attributes (age, cgpa, location, role) as separate keys in the 'properties' object.\n"
                            "4. RELATIONSHIPS: Ensure 'source' and 'target' match the explicit node IDs exactly."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Extract entities and relationships from the following text fragment: \n\n{chunk}"
                    }
                ],
                tools=[
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
                                                "properties": {"type": "object", "description": "Key-value pairs of attributes, e.g. {'cgpa': '9.0'}"}
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
                ],
                tool_choice={"type": "function", "function": {"name": "create_knowledge_graph"}}
            )
            
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                 print(f"Chunk {i+1}: No extraction results.")
                 continue
                 
            graph_data = tool_calls[0].function.arguments
            data = json.loads(graph_data)
            
            # Normalize and Aggregation
            def normalize_id(s):
                if not s: return s
                return re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_')

            for node in data.get("nodes", []):
                nid = normalize_id(node['id'])
                node['id'] = nid
                # Merge properties if node exists
                if nid in aggregated_nodes:
                    existing_props = aggregated_nodes[nid].get('properties', {})
                    new_props = node.get('properties', {})
                    existing_props.update(new_props)
                    aggregated_nodes[nid]['properties'] = existing_props
                else:
                    aggregated_nodes[nid] = node
            
            for edge in data.get("edges", []):
                edge['source'] = normalize_id(edge['source'])
                edge['target'] = normalize_id(edge['target'])
                aggregated_edges.append(edge)
                
            print(f"Chunk {i+1}: Extracted {len(data.get('nodes',[]))} nodes, {len(data.get('edges',[]))} edges.")

        except Exception as e:
            print(f"Error processing chunk {i+1}: {e}")

    # Final Combined Result
    combined_data = {
        "nodes": list(aggregated_nodes.values()),
        "edges": aggregated_edges
    }
    
    print(f"DEBUG Final Extraction: {len(combined_data['nodes'])} nodes, {len(combined_data['edges'])} edges.")
    return combined_data

from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError

def load_graph_to_neo4j(graph_data: dict):
    """
    Loads the extracted graph data into a Neo4j database with enhanced error logging.
    """
    # Ensure environment variables are set (assuming they are defined elsewhere)
    # Example:
    # NEO4J_URI = os.getenv("NEO4J_URI")
    # NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
    # NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        raise ValueError("Neo4j environment variables (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD) are not set.")

    if not graph_data:
        print("No graph data to load.")
        return

    print("Loading graph data into Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    node_labels = {node['id']: node['label'] for node in graph_data.get("nodes", [])}

    with driver.session() as session:
        # --- Create nodes with enhanced logging ---
        for node in graph_data.get("nodes", []):
            try:
                # FIXED: Added backticks (`) around the label to handle spaces or special characters.
                cypher_query = f"MERGE (n:`{node['label']}` {{id: $id}}) SET n += $properties"
                session.run(
                    cypher_query,
                    id=node['id'],
                    properties=node.get('properties', {})
                )
                print(f"  - SUCCESS: Merged Node ({node['id']}:{node['label']}) with props {node.get('properties')}")
            except CypherSyntaxError as e:
                print(f"  - CYPHER ERROR on node {node['id']}: {e}")
                print(f"    Query: {cypher_query}")
            except Exception as e:
                print(f"  - FAILED to process node {node['id']}: {e}")

        # --- Create relationships with robust handling ---
        for edge in graph_data.get("edges", []):
            try:
                source_id = edge['source']
                target_id = edge['target']
                
                # Use known label or fallback to 'Entity' if the node wasn't in the explicit node list
                source_label = node_labels.get(source_id, "Entity")
                target_label = node_labels.get(target_id, "Entity")

                # We use MERGE for nodes here too, in case they weren't created in the node loop 
                # (found only in edge list), ensuring the relationship always has endpoints.
                cypher_query = (
                    f"MERGE (source:`{source_label}` {{id: $source_id}}) "
                    f"MERGE (target:`{target_label}` {{id: $target_id}}) "
                    f"MERGE (source)-[r:`{edge['label']}`]->(target) "
                    f"SET r += $properties"
                )
                session.run(
                    cypher_query,
                    source_id=source_id,
                    target_id=target_id,
                    properties=edge.get('properties', {})
                )
                print(f"  - SUCCESS: Merged Edge ({source_id})-[{edge['label']}]->({target_id})")
            except CypherSyntaxError as e:
                print(f"  - CYPHER ERROR on edge {edge['source']}->{edge['target']}: {e}")
                print(f"    Query: {cypher_query}")
            except Exception as e:
                print(f"  - FAILED to process edge {edge['source']}->{edge['target']}: {e}")

    driver.close()
    print("Graph loading complete.")

def display_all_nodes_and_relationships():
    """
    Query Neo4j and return lists of nodes and relationships as a dict.
    """
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        raise ValueError("Neo4j environment variables (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD) are not set.")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    nodes_out = []
    rels_out = []

    with driver.session() as session:
        nodes = session.run(
            "MATCH (n) "
            "RETURN id(n) AS internal_id, labels(n) AS labels, properties(n) AS props, n.id AS id"
        ).data()
        for rec in nodes:
            nodes_out.append({
                "internal_id": rec.get("internal_id"),
                "labels": rec.get("labels"),
                "id": rec.get("id"),
                "properties": rec.get("props")
            })

        rels = session.run(
            "MATCH (a)-[r]->(b) "
            "RETURN id(r) AS internal_id, type(r) AS type, properties(r) AS props, "
            "a.id AS source_id, labels(a) AS source_labels, b.id AS target_id, labels(b) AS target_labels"
        ).data()
        for rec in rels:
            rels_out.append({
                "internal_id": rec.get("internal_id"),
                "type": rec.get("type"),
                "properties": rec.get("props"),
                "source_id": rec.get("source_id"),
                "source_labels": rec.get("source_labels"),
                "target_id": rec.get("target_id"),
                "target_labels": rec.get("target_labels")
            })

    driver.close()
    return {"nodes": nodes_out, "relationships": rels_out}

def get_db_schema_text(driver) -> str:
    """Read labels, relationship types and property keys from the DB and return a short schema string."""
    try:
        labels = []
        rel_types = []
        prop_keys = []
        sample_ids = []
        with driver.session() as session:
            labels = [row[0] for row in session.run("CALL db.labels()").values()]
            rel_types = [row[0] for row in session.run("CALL db.relationshipTypes()").values()]
            prop_keys = [row[0] for row in session.run("CALL db.propertyKeys()").values()]
            # Fetch generic samples to help with ID matching
            res = session.run("MATCH (n) WHERE n.id IS NOT NULL RETURN n.id LIMIT 50")
            sample_ids = [r["n.id"] for r in res]

        text = (
            f"Labels: {labels}\n"
            f"RelationshipTypes: {rel_types}\n"
            f"PropertyKeys: {prop_keys}\n"
            f"Sample Node IDs: {sample_ids}\n"
            "When creating Cypher use only these exact label names, relationship types and property keys."
        )
        return text
    except Exception as e:
        print("Failed to fetch DB schema:", e)
        return ""

def translate_question_to_cypher(question: str, schema_text: str, previous: str = None, last_error: str = None) -> str:
    """
    Translate question -> Cypher with schema context.
    The model must output JSON {"cypher":"..."} or plain cypher; we try to parse.
    """
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    system = (
        "You convert a natural-language question about a Neo4j graph into a single Cypher statement ONLY.\n"
        "You MUST use exactly the labels, relationship types and property keys provided in the schema context.\n"
        "\n"
        "BROAD MATCHING FOR VAGUE/GENERAL QUERIES:\n"
        "   - If the user asks a GENERAL question with vague terms (e.g., 'facilities', 'labs', 'programs', 'courses'), use BROAD pattern matching.\n"
        "   - SYNONYM EXPANSION: Map common terms to their variations:\n"
        "     * 'lab' / 'laboratory' → also match 'institute', 'research', 'facility', 'center'\n"
        "     * 'facility' → also match 'lab', 'institute', 'center', 'building'\n"
        "     * 'professor' / 'teacher' → also match 'faculty', 'instructor', 'researcher'\n"
        "     * 'program' → also match 'course', 'degree', 'major'\n"
        "   - Use case-insensitive matching with toLower() for all text comparisons.\n"
        "   - Example for 'lab facilities': `MATCH (n) WHERE any(l IN labels(n) WHERE toLower(l) CONTAINS 'lab' OR toLower(l) CONTAINS 'institute' OR toLower(l) CONTAINS 'research' OR toLower(l) CONTAINS 'facility' OR toLower(l) CONTAINS 'center') RETURN n, labels(n) LIMIT 10`\n"
        "   - For university-related queries, search for nodes connected to or labeled with the university name.\n"
        "\n"
        "SYNONYM & SCHEMA MAPPING:\n"
        "   - You MUST map terms in the User Question to the EXACT Labels and Relationship Types in the provided SCHEMA.\n"
        "   - Example 1: User asks 'Who are the staff?'. Schema has :Professor. -> Query MATCH (n:Professor). Do NOT use :Staff.\n"
        "   - Example 2: User asks 'What classes does he take?'. Schema has :enrolled_in. -> Query MATCH (n)-[:enrolled_in]->(c).\n"
        "   - If a user term does not exist in the schema, find the semantically closest Label or Relationship Type from the provided lists.\n"
        "   - RELATIONSHIP TYPES: Be extremely careful with spaces. If Schema has 'is led by', output `[:`is led by`]`. Do not output `[:is_led_by]`.\n"
        "\n"
        "DIRECTIONALITY CORRECTION:\n"
        "   - 'X is led by Y' usually means (X)-[:led_by]->(Y) or (Y)-[:leads]->(X) depending on schema.\n"
        "   - Check the schema RelationshipTypes. If only one direction exists, conform to it.\n"
        "\n"
        "IMPORTANT: The database schema appears to use Labels as entity identifiers in some cases (e.g., (:Vinith), (:Artificial_Intelligence), (:Professor)).\n"
        "   - CHECK THE LABELS LIST FIRST. If the entity name user asks about appears in the Labels list, use that Label directly. Example: `MATCH (n:`Vinith`) RETURN n`.\n"
        "   - If the name is NOT a label, check the PropertyKeys. If 'id' is a string property, use `toLower(n.id) CONTAINS 'term'`.\n"
        "   - WARNING: Sample Node IDs might be numeric (e.g., '1', '2'). If so, searching `n.id = 'Vinith'` will FAIL. Rely on Labels or other properties in that case.\n"
        "SPELL CHECK / ID MATCHING: The schema includes 'Sample Node IDs'. Use them to resolve spelling mistakes or formatting differences.\n"
        "   - Example: User asks about 'vinith', Sample IDs has 'Vinith_Student' -> Query for 'Vinith_Student'.\n"
        "   - Example: User asks about 'northeastern' or 'NEU', Sample IDs has 'Northeastern_University' -> Query for 'Northeastern_University'.\n"
        "ATTRIBUTES vs RELATIONSHIPS: If the user asks for a specific attribute (e.g. 'CGPA', 'age', 'score') and that key is in PropertyKeys, prioritize returning `n.property` over finding a relationship.\n"
        "   - Correct: `MATCH (n:`Vinith`) RETURN n.cgpa` (if 'cgpa' is a property)\n"
        "   - Incorrect: `MATCH (n)-[:has]->(m) ...` (unless 'cgpa' is NOT a property)\n"
        "COMPOUND QUESTIONS: If the question asks for multiple things (e.g. 'What is X's age and who is their manager?'), combine property returns with relationship matches.\n"
        "   - Example: `MATCH (n:`Person`) WHERE toLower(n.id) CONTAINS 'x' OPTIONAL MATCH (n)-[:`managed by`]->(m) RETURN n.age, m.id`\n"
        "WARNING: The database contains fragmented data with inconsistent labels. STRONGLY PREFER queries that do NOT specify node labels unless you find an exact match in the Schema Labels list.\n"
        "   - If unsure of label: `MATCH (n) WHERE toLower(n.id) CONTAINS 'term' OR any(l IN labels(n) WHERE toLower(l) CONTAINS 'term') RETURN n, labels(n)`\n"
        "RELATIONSHIPS: Relationship types from the schema might contain spaces (e.g. 'is led by'). Use them EXACTLY as shown. Do NOT replace spaces with underscores.\n"
        "If a relationship type has spaces, you MUST wrap it in backticks, e.g. `MATCH (a)-[:`is led by`]->(b)`.\n"
        "PASSIVE RELATIONSHIPS: For relationships like 'created by', 'managed by', 'led by', the direction is usually (Object)-[:`created by`]->(Agent). Check the schema and think about the direction.\n"
        "AMBIGUITY: If multiple relationship types seem relevant (e.g. 'depends on' vs 'dependent on'), use `MATCH (a)-[r]->(b) WHERE type(r) IN ['depends on', 'dependent on']`.\n"
        "DATA RETURN: When returning nodes, ALWAYS include labels(node) in the RETURN clause (e.g., `RETURN n, labels(n)`). This is CRITICAL because the name is often solely in the label.\n"
        "\n**MULTI-HOP Retrieval**: If the user asks for people 'at' a university or 'studying under' someone, and no direct edge exists, TRY to find broad matches first.\n"
        "   - Example: 'Who teaches at Northeastern?' -> `MATCH (n) WHERE 'Northeastern University' IN labels(n) OR n.id CONTAINS 'Northeastern' MATCH (p) WHERE 'Professor' IN labels(p) OR 'Researcher' IN labels(p) RETURN p, labels(p)` (This is a simplified fallback if no relation exists).\n"
        "   - Prefer: `MATCH (n:Professor)-[:`teaching at`]-(u:University) ...` if exact relations exist.\n"
        "\nEXAMPLES:\n"
        "1. Q: Who created the dependency of the project led by Alice?\n"
        "   Cypher: MATCH (alice)-[:leads]->(project)-[r]->(dependency)-[:`created by`]->(creator) WHERE type(r) IN ['depends on', 'dependent on'] AND (toLower(alice.id) CONTAINS 'alice' OR 'Alice' IN labels(alice)) RETURN creator, labels(creator)\n"
        "2. Q: Which person that reports to Bob works on Project X?\n"
        "   Cypher: MATCH (p)-[:`reports to`]->(bob) MATCH (p)-[:`works on`]->(project) WHERE (toLower(bob.id) CONTAINS 'bob' OR 'Bob' IN labels(bob)) AND (toLower(project.id) CONTAINS 'project_x' OR 'Project_X' IN labels(project)) RETURN p, labels(p)\n"
        "3. Q: Find the name and role of the leader of the project that depends on a data pipeline managed by a team located in San Francisco, and state who that leader reports to.\n"
        "   Cypher: MATCH (team)-[:`located in`|`based in`|`works in`]-(loc) WHERE toLower(loc.id) CONTAINS 'san_francisco' MATCH (pipeline)-[:`manages`|`managed by`]-(team) MATCH (project)-[:`depends on`|`dependent on`]-(pipeline) MATCH (leader)-[:`leads`|`led by`]-(project) MATCH (leader)-[:`reports to`]->(boss) RETURN leader.id, leader.role, labels(leader), boss.id, labels(boss)\n"
        "   (Note: Use undirected relationships `MATCH (a)-[:REL]-(b)` when the direction is ambiguous (e.g. 'managed by' vs 'manages'). Only use directed arrows if certain.)\n"
        "4. Q: What is Vinith's CGPA?\n"
        "   Cypher: MATCH (n) WHERE 'Vinith' IN labels(n) OR toLower(n.id) CONTAINS 'vinith' RETURN n.cgpa, labels(n)\n"
        "5. Q: What is Vinith's CGPA and where is he planning to study?\n"
        "   Cypher: MATCH (n) WHERE 'Vinith' IN labels(n) OR toLower(n.id) CONTAINS 'vinith' OPTIONAL MATCH (n)-[:`planning to`|`plans to`|`studying in`]-(m) RETURN n.cgpa, m, labels(m)\n"
        "6. Q: Who are the professors Vinith needs to learn with at Northeastern?\n"
        "   Cypher: MATCH (v) WHERE 'Vinith' IN labels(v) OR toLower(v.id) CONTAINS 'vinith' MATCH (p) WHERE 'Professor' IN labels(p) OR 'Researcher' IN labels(p) RETURN p, labels(p)\n"
        "   (Note: If no direct relation like 'learns with' exists, return the target entities directly based on labels.)\n"
        "7. Q: What are the lab facilities at Northeastern University?\n"
        "   Cypher: MATCH (n) WHERE any(l IN labels(n) WHERE toLower(l) CONTAINS 'lab' OR toLower(l) CONTAINS 'institute' OR toLower(l) CONTAINS 'research' OR toLower(l) CONTAINS 'facility') RETURN n, labels(n) LIMIT 10\n"
        "\nReturn JSON with a single field {\"cypher\":\"...\"} or a plain Cypher statement. Do not add extra explanation."
        f"\n\nSCHEMA:\n{schema_text}"
    )

    user = question
    if previous:
        user += f"\n\nPrevious attempt:\n{previous}"
    if last_error:
        user += f"\n\nPrevious error/notes:\n{last_error}"

    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0
        )
        content = resp.choices[0].message.content.strip()
    except Exception as e:
        print("translate_question_to_cypher error:", e)
        return None

    # try strict JSON -> "cypher"
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and parsed.get("cypher"):
            return parsed["cypher"].strip()
    except Exception:
        pass

    # code fence
    m = re.search(r"```(?:cypher)?\s*(.*?)```", content, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # try to find first valid cypher statement (starts with MATCH/CREATE/MERGE/RETURN/UNWIND/CALL)
    m2 = re.search(r"(?i)\b(MATCH|CREATE|MERGE|CALL|UNWIND|RETURN|WITH)\b.*", content, re.DOTALL)
    if m2:
        return m2.group(0).strip()

    # nothing found
    print("No Cypher detected in model response:", content[:200])
    return None

def sanitize_cypher(cypher: str, schema_text: str) -> str:
    """
    Fix obvious model mistakes:
     - adjacent property maps -> merge into a single map
     - remove duplicated single-quotes
     - create a stable variable name for anonymous nodes with property maps so queries don't break
     - wrap label and rel names in backticks where appropriate
    """
    if not cypher or not schema_text:
        return cypher

    # merge adjacent property maps like "{...}{...}" -> "{..., ...}"
    cypher = re.sub(r"\}\s*\{", ", ", cypher)

    # collapse duplicate single quotes that LLM sometimes emits: ''foo'' -> 'foo'
    cypher = re.sub(r"'{2,}", "'", cypher)

    # ensure backticks for labels & relationship types (safe-guard)
    cypher = re.sub(r":\s*([A-Za-z0-9_]+)(?=[\s\{\)\]])", lambda m: f":`{m.group(1)}`", cypher)

    # convert anonymous nodes with property maps into named ones, e.g. 
    # (:`Project` {name: 'Odyssey'}) -> (pr:`Project` {name: 'Odyssey'})
    def _anon_to_named(m):
        label = m.group(1).strip("`")
        props = m.group(2).strip()
        base = re.sub(r'\W+', '', label.lower())
        var = (base[:3] or "n")
        # make sure property string has no duplicate braces leftover (already merged above)
        return f"({var}:`{label}` {{{props}}})"

    cypher = re.sub(r"\(\s*`?([A-Za-z0-9_]+)`?\s*\{\s*([^}]+?)\s*\}\s*\)", _anon_to_named, cypher)

    # final cleanup: remove stray backslashes and normalize spacing
    cypher = cypher.replace(r"\ ", " ").replace("\\", "")
    cypher = re.sub(r"\s{2,}", " ", cypher).strip()

    return cypher


def results_to_nl(question: str, cypher: str, results: list) -> str:
    """
    Convert query results into a concise natural-language answer using OpenAI.
    """
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    try:
        snippet = json.dumps(results if len(results) <= 20 else results[:20], indent=2)
    except Exception:
        snippet = str(results)
    system = "You are a concise assistant that answers user questions using query results."
    user = (
        f"Question: {question}\n\n"
        f"Cypher: {cypher}\n\n"
        f"Results (truncated): {snippet}\n\n"
        "Provide a short direct answer. If results empty reply: 'No information found.'"
    )
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"results_to_nl error: {e}")
        return "Could not generate an NLP answer."


def ask_graph(question: str, max_retries: int = 5) -> dict:
    """
    Use schema-aware translator and run query. If empty results or errors, retry once with context.
    Returns dict {cypher, results, nl_answer, error}
    """
    out = {"cypher": None, "results": None, "nl_answer": None, "error": None}

    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        out["error"] = "Neo4j credentials not set."
        return out

    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        schema_text = get_db_schema_text(driver)
    except Exception as e:
        out["error"] = f"Failed to connect / retrieve schema: {e}"
        if driver:
            driver.close()
        return out

    prev_query = None
    last_error = None

    for attempt in range(max_retries):
        cypher = translate_question_to_cypher(question, schema_text, previous=prev_query, last_error=last_error)
        out["cypher_raw"] = cypher
        if cypher:
            cypher = sanitize_cypher(cypher, schema_text)
            out["cypher"] = cypher

        if not cypher:
            last_error = "Model did not return a valid Cypher."
            continue

        # Execute query
        try:
            with driver.session() as session:
                records = session.run(cypher).data()
            out["results"] = records
            if records:
                out["nl_answer"] = results_to_nl(question, cypher, records)
                driver.close()
                return out
            # zero results — try refine once, give model the schema + info about zero results
            last_error = "Query returned zero results."
            prev_query = cypher
            continue
        except Exception as e:
            last_error = f"Execution error: {e}"
            prev_query = cypher
            # short backoff before retrying
            time.sleep(0.2)
            continue

    driver.close()
    out["error"] = f"No usable results after {max_retries} attempts. Last query: {prev_query}. Last error/notes: {last_error}"
    return out

# --- Streamlit UI only (clean single block, do NOT call run_streamlit in __main__) ---
try:
    import streamlit as st

    DEFAULT_SAMPLE = """
    The Odyssey Project is led by Anya Sharma, who works in the Berlin Office. Odyssey started on May 15, 2023, and is critically dependent on the Neptune Data Pipeline. The Neptune Pipeline, which is a data science asset, is managed by the Data Science Team. The Data Science Team is located in San Francisco. The person who created the initial Neptune architecture is Dr. Elias Vance. Anya Sharma is a Senior Engineer. Anya Sharma reports to Director Lina Chen. Dr. Elias Vance and Javier Rodriguez both report to Director Lina Chen.
    """

    def run_streamlit():
        st.title("Knowledge Graph — Extract & Load")
        text = st.text_area("Input text", value=DEFAULT_SAMPLE, height=200)

        # Extraction
        if st.button("Extract entities & relationships"):
            with st.spinner("Extracting..."):
                extracted = extract_entities_and_relations(text)
            if extracted:
                st.success("Extraction complete")
                st.session_state["extracted"] = extracted
                st.json(extracted)
            else:
                st.error("Extraction failed. Check logs.")

        # Load to Neo4j
        if st.button("Load extracted graph to Neo4j"):
            data = st.session_state.get("extracted")
            if not data:
                st.warning("No extracted data in session — extracting now.")
                data = extract_entities_and_relations(text)
            if data:
                with st.spinner("Loading to Neo4j..."):
                    load_graph_to_neo4j(data)
                st.success("Loaded to Neo4j")

        # Display stored graph
        if st.button("Display all nodes & relationships from Neo4j"):
            with st.spinner("Querying Neo4j..."):
                graph = display_all_nodes_and_relationships()
            st.subheader("Nodes")
            st.json(graph.get("nodes"))
            st.subheader("Relationships")
            st.json(graph.get("relationships"))
        st.markdown("---")
        st.subheader("Ask the graph (natural language)")
        q = st.text_input("Your question", value="Who leads the Odyssey project?")
        if st.button("Ask"):
            if not q.strip():
                st.warning("Enter a question first.")
            else:
                with st.spinner("Translating and querying..."):
                    out = ask_graph(q)
                    if out["error"]:
                        st.error(f"Error: {out['error']}")
                    else:
                        st.code(out["cypher"], language="cypher")
                        st.subheader("Results (raw)")
                        st.json(out["results"])
                        st.subheader("Answer (NLP)")
                        st.write(out["nl_answer"])
        st.markdown("---")
        st.info(
            "This demo showcases extraction of entities and relationships from text, "
            "loading into a Neo4j graph, and querying the graph using natural language questions."
        )

    # Only run UI when Streamlit is executing this script (avoids CLI run)
    if os.environ.get("STREAMLIT_RUN_MAIN"):
        run_streamlit()

except Exception:
    # If streamlit isn't installed or UI failed, do nothing.
    pass

if __name__ == "__main__":
    # This is the unstructured text we want to convert into a knowledge graph.
    run_streamlit()