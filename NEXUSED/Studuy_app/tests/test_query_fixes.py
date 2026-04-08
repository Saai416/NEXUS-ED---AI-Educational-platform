"""
Test script to verify query retrieval fixes.
Tests various query types to ensure the system properly retrieves information
from Pinecone and/or Neo4j.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from integrated_app import app
except ImportError:
    print("Error: Could not import integrated_app. Make sure you're in the correct directory.")
    sys.exit(1)

# Test cases
TEST_CASES = [
    {
        "name": "Original Failing Query",
        "question": "What are the lab facilities in northeastern university?",
        "namespace": "**NEU**",
        "expected": "Should return information about labs/institutes"
    },
    {
        "name": "Vague Query - Research Labs",
        "question": "Tell me about research labs at NEU",
        "namespace": "**NEU**",
        "expected": "Should return lab/research information"
    },
    {
        "name": "Vague Query - Facilities",
        "question": "What facilities does Northeastern have?",
        "namespace": "**NEU**",
        "expected": "Should return facility information"
    },
    {
        "name": "Specific Query - Professors",
        "question": "Who are the professors at Northeastern?",
        "namespace": "**NEU**",
        "expected": "Should return professor information"
    },
    {
        "name": "Specific Query - Programs",
        "question": "What programs does the university offer?",
        "namespace": "**NEU**",
        "expected": "Should return program information"
    }
]

async def test_query(test_case):
    """Test a single query."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*80}")
    print(f"Question: {test_case['question']}")
    print(f"Namespace: {test_case['namespace']}")
    print(f"Expected: {test_case['expected']}")
    print(f"-"*80)
    
    try:
        inputs = {
            "question": test_case["question"],
            "namespace": test_case["namespace"]
        }
        
        result = await app.ainvoke(inputs)
        
        answer = result.get("final_answer", "No answer generated")
        vector_results = result.get("vector_results", [])
        graph_results = result.get("graph_results", {})
        
        print(f"\n✓ ANSWER:")
        print(f"  {answer}")
        
        print(f"\n📊 SOURCE BREAKDOWN:")
        print(f"  Vector Results: {len(vector_results)} matches")
        print(f"  Graph Results: {'Yes' if graph_results and graph_results.get('nl_answer') else 'No'}")
        
        # Determine success
        has_answer = answer and answer.lower() != "i don't know."
        success = "✅ PASS" if has_answer else "❌ FAIL"
        print(f"\n{success}")
        
        return {
            "name": test_case["name"],
            "success": has_answer,
            "answer": answer,
            "vector_count": len(vector_results),
            "has_graph": bool(graph_results and graph_results.get('nl_answer'))
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "name": test_case["name"],
            "success": False,
            "error": str(e)
        }

async def run_tests():
    """Run all test cases."""
    print("\n" + "="*80)
    print("QUERY RETRIEVAL FIX - TEST SUITE")
    print("="*80)
    
    results = []
    for test_case in TEST_CASES:
        result = await test_query(test_case)
        results.append(result)
        await asyncio.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    for result in results:
        status = "✅" if result.get("success") else "❌"
        print(f"{status} {result['name']}")
        if not result.get("success") and "error" in result:
            print(f"   Error: {result['error']}")
    
    print(f"\n{'='*80}")
    print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")
    
    return passed == total

if __name__ == "__main__":
    print("\n🚀 Starting test suite...")
    print("Note: Make sure you have uploaded content to the '**NEU**' namespace in Pinecone")
    print("and have relevant data in Neo4j about Northeastern University.\n")
    
    success = asyncio.run(run_tests())
    
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Review the output above.")
        sys.exit(1)
