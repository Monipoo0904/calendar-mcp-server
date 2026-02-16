#!/usr/bin/env python3
"""Quick test of research_and_breakdown function"""
import sys
sys.path.insert(0, '/Users/moni/Desktop/Scratchwerk/Projects/vercel-event-calendar-mcp')

from main import research_and_breakdown

# Test the function directly
result = research_and_breakdown(goal="build an iOS app", deadline="2026-03-05")
print("Result type:", type(result))
print("Result keys:", result.keys() if isinstance(result, dict) else "not a dict")
print("\nFull result:")
import json
print(json.dumps(result, indent=2))
