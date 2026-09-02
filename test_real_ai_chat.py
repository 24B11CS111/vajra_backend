import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 1. Login
print("=== 1. AUTHENTICATING ===")
login_res = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "user_a@vajra.ai", "password": "Password123!"},
    timeout=5
)
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("Logged in. JWT token acquired.")

# 2. Create Conversation
print("\n=== 2. CREATING CONVERSATION ===")
conv_res = requests.post(
    f"{BASE_URL}/chat/conversations",
    headers=headers,
    json={"title": "Real AI Test Conversation"},
    timeout=5
)
assert conv_res.status_code == 200, f"Create conversation failed: {conv_res.text}"
conv_id = conv_res.json()["id"]
print(f"Conversation created: {conv_id}")

# 3. Stream Message 1: "Hello VAJRA"
print("\n=== 3. STREAMING REAL AI MESSAGE 1: 'Hello VAJRA' ===")
stream_res = requests.post(
    f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
    headers=headers,
    json={"role": "user", "content": "Hello VAJRA! Who are you?"},
    stream=True,
    timeout=30
)
assert stream_res.status_code == 200, f"Stream failed: {stream_res.text}"

print("AI Streamed Output: ", end="", flush=True)
full_reply_1 = []
for line in stream_res.iter_lines():
    if line:
        decoded = line.decode("utf-8")
        if decoded.startswith("data: "):
            chunk = json.loads(decoded[6:])
            if "delta" in chunk:
                full_reply_1.append(chunk["delta"])
                print(chunk["delta"], end="", flush=True)
            elif chunk.get("done"):
                print("\n[STREAM 1 FINISHED]")
assert len(full_reply_1) > 0, "No tokens received from AI!"

# 4. Stream Message 2: "What is quantum mechanics?"
print("\n=== 4. STREAMING REAL AI MESSAGE 2: 'What is quantum mechanics?' ===")
stream_res_2 = requests.post(
    f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
    headers=headers,
    json={"role": "user", "content": "What is quantum mechanics in 2 sentences?"},
    stream=True,
    timeout=30
)
assert stream_res_2.status_code == 200, f"Stream 2 failed: {stream_res_2.text}"

print("AI Streamed Output: ", end="", flush=True)
full_reply_2 = []
for line in stream_res_2.iter_lines():
    if line:
        decoded = line.decode("utf-8")
        if decoded.startswith("data: "):
            chunk = json.loads(decoded[6:])
            if "delta" in chunk:
                full_reply_2.append(chunk["delta"])
                print(chunk["delta"], end="", flush=True)
            elif chunk.get("done"):
                print("\n[STREAM 2 FINISHED]")
assert len(full_reply_2) > 0, "No tokens received from AI!"

# 5. Verify Persistence
print("\n=== 5. VERIFYING CONVERSATION MESSAGE PERSISTENCE IN DATABASE ===")
time.sleep(1)
msg_res = requests.get(
    f"{BASE_URL}/chat/conversations/{conv_id}/messages",
    headers=headers,
    timeout=5
)
assert msg_res.status_code == 200
messages = msg_res.json()
print(f"Persisted messages in conversation: {len(messages)}")
for idx, m in enumerate(messages):
    print(f"  [{idx+1}] {m['role'].upper()}: {m['content'][:80]}...")

print("\n>>> FASTAPI CHAT ENDPOINT WITH REAL AI STREAMING FULLY VERIFIED! <<<")
