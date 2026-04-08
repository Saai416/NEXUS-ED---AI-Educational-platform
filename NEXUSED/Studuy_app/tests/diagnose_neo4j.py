
import os
import sys
from neo4j import GraphDatabase, exceptions

# Hardcoded credentials from KG2.py
NEO4J_URI="neo4j+s://ba74b87c.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="RIjZjP4J7SNOFNlpnaDw_boP5i50OpL5-d1E6ZNOhe4"

def test_connection():
    print("--- [Diagnostic] Testing Neo4j Connection ---")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        
        # Verify connectivity
        driver.verify_connectivity()
        print("Success: Connected to Neo4j!")

        with driver.session() as session:
            # Check Node Count
            count_res = session.run("MATCH (n) RETURN count(n) AS count").single()
            node_count = count_res["count"] if count_res else 0
            print(f"Total Nodes: {node_count}")

            # Check Sample Schema
            if node_count > 0:
                print("\nSampling first 5 nodes:")
                nodes = session.run("MATCH (n) RETURN labels(n) as labels, n.id as id, properties(n) as props LIMIT 5")
                for record in nodes:
                    print(f" - Labels: {record['labels']}, ID: {record['id']}, Props keys: {list(record['props'].keys())}")
            else:
                 print("Database is empty.")

            # Check specific nodes to understand structure
            print("\nChecking 'Vinith' node:")
            vinith = session.run("MATCH (n) WHERE toLower(n.id) CONTAINS 'vinith' OR 'Vinith' IN labels(n) RETURN labels(n), n.id, properties(n) LIMIT 1").single()
            if vinith:
                 print(f"Found Vinith: Labels={vinith['labels(n)']}, ID={vinith['n.id']}, Props={vinith['properties(n)']}")
            else:
                 print("Vinith node NOT found by ID or Label.")

            print("\nChecking 'Artificial Intelligence' node:")
            ai = session.run("MATCH (n) WHERE 'Artificial Intelligence' IN labels(n) RETURN labels(n), n.id, properties(n) LIMIT 1").single()
            if ai:
                 print(f"Found AI: Labels={ai['labels(n)']}, ID={ai['n.id']}, Props={ai['properties(n)']}")
            else:
                 print("AI node NOT found by Label.")


        driver.close()
        return True

    except exceptions.ServiceUnavailable as e:
        print(f"Connection Failed: Service Unavailable. Check internet or if DB is paused. Error: {e}")
        return False
    except exceptions.AuthError as e:
        print(f"Connection Failed: Auth Error. Check username/password. Error: {e}")
        return False
    except Exception as e:
        print(f"Connection Failed: Generic Error. {e}")
        return False

if __name__ == "__main__":
    test_connection()
