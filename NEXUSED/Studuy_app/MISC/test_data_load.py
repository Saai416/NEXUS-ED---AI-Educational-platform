import os
from neo4j import GraphDatabase

NEO4J_URI="neo4j+s://ba74b87c.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="RIjZjP4J7SNOFNlpnaDw_boP5i50OpL5-d1E6ZNOhe4"

def test_load():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    print("Test 1: Connect")
    try:
        driver.verify_connectivity()
        print("Connected.")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    print("Test 2: Write Node")
    try:
        with driver.session() as session:
            # Create a test node
            session.run("MERGE (n:TestNode {id: 'TestVinith'}) SET n.cgpa = '9.99'")
            print("Write successful.")
            
            # Read it back
            res = session.run("MATCH (n:TestNode {id: 'TestVinith'}) RETURN n.id, n.cgpa")
            record = res.single()
            if record:
                print(f"Read back: {record}")
            else:
                print("Read back FAILED.")
                
            # Check properties again
            res = session.run("CALL db.propertyKeys()")
            keys = [r[0] for r in res]
            print(f"Property Keys now: {keys}")
            
    except Exception as e:
        print(f"Write failed: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    test_load()
