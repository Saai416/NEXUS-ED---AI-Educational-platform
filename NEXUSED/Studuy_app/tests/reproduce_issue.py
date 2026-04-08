import os
import sys
import json
from KG2 import extract_entities_and_relations, translate_question_to_cypher, get_db_schema_text, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from neo4j import GraphDatabase

text = """After detailed research, I have decided to pursue the MS in Artificial Intelligence program at 
Northeastern University, Boston. The comprehensive curriculum, such as NLP and Robotics and Agent
Based Systems and and dynamic learning environment with a highly interdisciplinary curriculum 
combining Computer Science and Engineering, and state-of-the-art lab facilities, such as the Institute 
for Experiential AI, and Robotics & Intelligent Vehicles Research Laboratory (RIVeR), are poised to be 
catalysts for my personal and academic growth. At the university, I want to be part of innovative 
research projects, such as initiatives within the Institute for Experiential AI – a major University-wide 
research hub, which acts as a forefront for Human-centric AI solutions to handle challenges in health 
and life sciences, to orchestrate human-in-the-loop systems, and to ensure responsible AI ethics. 
Furthermore, I am eager to study under Dr Usama Fayyad, whose research focuses on data mining and 
Experiential AI, Dr. David Bau, whose research focuses on interpreting and manipulating deep 
learning models, aligning perfectly with my own interests. Apart from academics, I want to join the 
university’s AWS Cloud Club and Northeastern University Cricket Clubs, which will ensure an all
rounded development of my career ambitions and personality."""

print("--- TESTING EXTRACTION ---")
if not os.getenv("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in env.")

try:
    data = extract_entities_and_relations(text)
    print("Extracted Data:", json.dumps(data, indent=2))
except Exception as e:
    print("Extraction failed:", e)
    data = None

print("\n--- TESTING CONNECTION & SCHEMA ---")
driver = None
schema = ""
try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("Connected to Neo4j.")
    schema = get_db_schema_text(driver)
    # print("Schema:", schema) # Reduce output noise
except Exception as e:
    print(f"Neo4j connection failed: {e}")

print("\n--- TESTING QUERY TRANSLATION ---")
question = "which are the professors with whom vinith needs to learn in northeastern university?"
if schema:
    cypher = translate_question_to_cypher(question, schema)
    print("Generated Cypher:", cypher)
else:
    print("Skipping translation due to missing schema.")

if driver:
    driver.close()
