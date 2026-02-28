"""End-to-end test: run agent with real dataset + Gemini API."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import run_agent

query = "What is the average transaction amount for bill payments?"
print(f"Query: {query}")
print("=" * 60)

result = run_agent(query)

print(f"\nMode: {result['mode']}")
print(f"Steps: {len(result['steps'])}")
print(f"Success: {result['result'].get('success', False)}")

if result.get('code'):
    print(f"\n--- Generated Code ---")
    print(result['code'])

print(f"\n--- Response ---")
print(result['response'])

if result.get('followups'):
    print(f"\n--- Follow-ups ---")
    for f in result['followups']:
        print(f"  -> {f}")

print(f"\n--- Verdict ---")
v = result.get('verdict', {})
print(f"Judge ran: {v.get('judge_ran', False)}")
if v.get('judge_ran'):
    print(f"Approved: {v.get('approved')}")
    print(f"Scores: {v.get('scores', {})}")
