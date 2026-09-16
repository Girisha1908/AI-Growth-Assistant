import requests
import json

BASE_URL = "http://localhost:8000"

print("--- Step 1: Create Session ---")
res = requests.post(f"{BASE_URL}/sessions")
print("Status:", res.status_code)
session_data = res.json()
print("Created session:", session_data)
session_id = session_data["session_id"]

print("\n--- Step 2: Turn 1: Ask Initial Question ---")
q1 = "How should product teams approach improving user retention?"
print(f"User: {q1}")
res1 = requests.post(
    f"{BASE_URL}/chat",
    json={"session_id": session_id, "message": q1},
    timeout=300,
)
print("Status:", res1.status_code)
data1 = res1.json()
print("Assistant Answer:\n", data1.get("answer"))
print("Sources:", data1.get("sources"))

print("\n--- Step 3: Turn 2: Ask Follow-up Question in Same Session ---")
q2 = "What about specifically in the first week?"
print(f"User: {q2}")
res2 = requests.post(
    f"{BASE_URL}/chat",
    json={"session_id": session_id, "message": q2},
    timeout=300,
)
print("Status:", res2.status_code)
data2 = res2.json()
print("Assistant Answer:\n", data2.get("answer"))
print("Sources:", data2.get("sources"))

print("\n--- Step 4: GET /sessions/{session_id}/messages ---")
res_history = requests.get(f"{BASE_URL}/sessions/{session_id}/messages")
print("History Status:", res_history.status_code)
history = res_history.json()
print(f"Total messages in history: {len(history)}")
for idx, msg in enumerate(history, 1):
    preview = msg['content'][:120].replace('\n', ' ')
    print(f"[{idx}] Role: {msg['role']} | Time: {msg['created_at']} | Content: {preview}...")
