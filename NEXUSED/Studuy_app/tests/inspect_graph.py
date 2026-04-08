import os
from neo4j import GraphDatabase
from KG2 import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, get_db_schema_text

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

print("--- SCHEMA ---")
print(get_db_schema_text(driver))

print("\n--- VINITH'S CONNECTIONS ---")
with driver.session() as session:
    res = session.run("MATCH (n) WHERE toLower(n.id) CONTAINS 'vinith' OR 'Vinith' IN labels(n) OPTIONAL MATCH (n)-[r]-(m) RETURN n.id, labels(n), type(r), m.id, labels(m)")
    data = res.data()
    if not data:
        print("No 'Vinith' node found.")
    else:
        for row in data:
            print(f"{row['n.id']} ({row['labels(n)']}) --[{row['type(r)']}]--> {row['m.id']} ({row['labels(m)']})")

driver.close()
