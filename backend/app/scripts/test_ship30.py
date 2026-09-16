"""Verification script for the Ship 30 content generation skill."""

import json
import requests

BASE_URL = "http://localhost:8000"

print("--- Step 1: Create Session ---")
res_session = requests.post(f"{BASE_URL}/sessions")
print("Session status:", res_session.status_code)
session_data = res_session.json()
session_id = session_data["session_id"]
print(f"Session ID: {session_id}")

print("\n--- Step 2: Call POST /skills/ship30 ---")
topic = "user retention strategies"
payload = {
    "session_id": session_id,
    "topic": topic,
}
print(f"Submitting topic: '{topic}'...")

res_skill = requests.post(f"{BASE_URL}/skills/ship30", json=payload, timeout=600)
print("Skill Status:", res_skill.status_code)
data = res_skill.json()

essay = data.get("essay", "")
word_count = data.get("word_count", 0)
sources = data.get("sources", [])

print("\n" + "=" * 80)
print("FULL GENERATED SHIP 30 ESSAY:")
print("=" * 80)
print(essay)
print("=" * 80)

print(f"\nWord Count: {word_count} words")
print(f"Character Count: {len(essay)} characters")
print("Cited Sources:")
for s in sources:
    print(f" - {s['source_file']} (chunk {s['chunk_index']})")

print("\n--- Step 3: Verify Persistence in Session History ---")
res_history = requests.get(f"{BASE_URL}/sessions/{session_id}/messages")
print("History Status:", res_history.status_code)
history = res_history.json()
print(f"Total messages stored in session: {len(history)}")
for idx, msg in enumerate(history, 1):
    preview = msg['content'][:100].replace('\n', ' ')
    print(f" [{idx}] {msg['role'].upper()}: {preview}...")
