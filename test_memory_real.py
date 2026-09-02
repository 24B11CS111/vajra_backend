import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 1. Login
login_res = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "user_a@vajra.ai", "password": "Password123!"},
    timeout=5
)
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Create Conversation
conv_res = requests.post(
    f"{BASE_URL}/chat/conversations",
    headers=headers,
    json={"title": "Memory Test Conversation"},
    timeout=5
)
conv_id = conv_res.json()["id"]

# 3. Store Memory Message: "Remember that I prefer studying at night."
print("=== 1. SENDING MEMORY STORE MESSAGE ===")
stream_res = requests.post(
    f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
    headers=headers,
    json={"role": "user", "content": "Remember that I prefer studying at night."},
    stream=True,
    timeout=30
)
reply = []
for line in stream_res.iter_lines():
    if line:
        decoded = line.decode("utf-8")
        if decoded.startswith("data: "):
            c = json.loads(decoded[6:])
            if "delta" in c:
                reply.append(c["delta"])
print("AI Response:", "".join(reply))

# Wait for background memory extraction pipeline
print("Waiting 3 seconds for background memory pipeline...")
time.sleep(3)

# 4. Check Saved Memories
mem_res = requests.get(f"{BASE_URL}/memory/", headers=headers, timeout=5)
memories = mem_res.json()
print(f"\nSaved Memories in DB ({len(memories)} total):")
for m in memories:
    print(f"  - [{m['memory_type'].upper()}] {m['content']} (importance={m['importance']}, conf={m['confidence']})")

# 5. Query Memory: "When do I prefer studying?"
print("\n=== 2. QUERYING SAVED MEMORY ===")
query_res = requests.post(
    f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
    headers=headers,
    json={"role": "user", "content": "When do I prefer studying?"},
    stream=True,
    timeout=30
)
query_reply = []
for line in query_res.iter_lines():
    if line:
        decoded = line.decode("utf-8")
        if decoded.startswith("data: "):
            c = json.loads(decoded[6:])
            if "delta" in c:
                query_reply.append(c["delta"])

print("AI Response to Memory Query:\n", "".join(query_reply))
