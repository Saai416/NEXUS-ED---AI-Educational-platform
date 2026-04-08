import os
from neo4j import GraphDatabase

NEO4J_URI="neo4j+s://ba74b87c.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="RIjZjP4J7SNOFNlpnaDw_boP5i50OpL5-d1E6ZNOhe4"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

with driver.session() as session:
    print("--- Property Keys ---")
    res = session.run("CALL db.propertyKeys()")
    print([r[0] for r in res])

    print("\n--- Vinith Node ---")
    res = session.run("MATCH (n) WHERE toLower(n.id) CONTAINS 'vinith' RETURN labels(n), n.id, properties(n)")
    for record in res:
        print(record.data())

driver.close()
