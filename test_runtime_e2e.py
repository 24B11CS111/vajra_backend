import requests
import json

base_url = "http://127.0.0.1:8000/api/v1"

print("=== 1. TEST LOGIN (USER A) ===")
res = requests.post(f"{base_url}/auth/login", json={"email": "user_a@vajra.ai", "password": "password123"})
assert res.status_code == 200, f"Login failed: {res.text}"
token_a = res.json()["access_token"]
headers_a = {"Authorization": f"Bearer {token_a}"}
print("User A logged in successfully. Token acquired.")

print("=== 2. TEST USER PROFILE (GET /me) ===")
res = requests.get(f"{base_url}/me", headers=headers_a)
assert res.status_code == 200, f"Get profile failed: {res.text}"
user_a = res.json()
print(f"Profile retrieved: email={user_a.get('email')}, id={user_a.get('id')}")

print("=== 3. TEST CONVERSATION & SSE STREAM ===")
res = requests.post(f"{base_url}/chat/conversations", json={"title": "Autonomous Companion Session"}, headers=headers_a)
assert res.status_code == 200, f"Create conversation failed: {res.text}"
conv_id = res.json()["id"]
print(f"Conversation created: {conv_id}")

stream_res = requests.post(
    f"{base_url}/chat/conversations/{conv_id}/messages/stream",
    json={"role": "user", "content": "Hello VAJRA, remember that my major is Astrophysics."},
    headers=headers_a,
    stream=True
)
assert stream_res.status_code == 200, f"Stream failed: {stream_res.text}"
chunks = []
for line in stream_res.iter_lines():
    if line:
        chunks.append(line.decode("utf-8"))
print(f"SSE stream received {len(chunks)} events.")

print("=== 4. TEST MEMORY LIFECYCLE ===")
res = requests.post(f"{base_url}/memory/", json={
    "content": "User is majoring in Astrophysics with focus on dark matter.",
    "memory_type": "fact",
    "importance": 0.95,
    "source": "Explicit Input"
}, headers=headers_a)
assert res.status_code == 201, f"Create memory failed: {res.text}"
mem_id = res.json()["id"]
print(f"Memory created: {mem_id}")

res = requests.get(f"{base_url}/memory/", headers=headers_a)
assert res.status_code == 200, f"Get memories failed: {res.text}"
memories = res.json()
assert any(m["id"] == mem_id for m in memories), "Created memory not in list"
print(f"Memory retrieved successfully ({len(memories)} total).")

res = requests.post(f"{base_url}/memory/{mem_id}/favorite", headers=headers_a)
assert res.status_code == 200, f"Favorite memory failed: {res.text}"
print("Memory pinned/favorited.")

print("=== 5. TEST PLANNER ENGINE LIFECYCLE ===")
res = requests.post(f"{base_url}/planner/tasks", json={
    "title": "Revise General Relativity Chapter 4",
    "category": "Study",
    "priority": "high",
    "is_completed": False
}, headers=headers_a)
assert res.status_code == 201, f"Create task failed: {res.text}"
task_id = res.json()["id"]
print(f"Planner task created: {task_id}")

res = requests.post(f"{base_url}/planner/tasks/{task_id}/toggle", headers=headers_a)
assert res.status_code == 200, f"Toggle task failed: {res.text}"
assert res.json()["is_completed"] == True
print("Task toggled to completed.")

print("=== 6. TEST NOTIFICATIONS ===")
res = requests.post(f"{base_url}/notifications/", json={
    "title": "Study Session Starting Soon",
    "message": "Your 8:00 PM session on General Relativity starts in 15 minutes.",
    "type": "reminder"
}, headers=headers_a)
assert res.status_code == 201, f"Create notification failed: {res.text}"
notif_id = res.json()["id"]
print(f"Notification created: {notif_id}")

res = requests.post(f"{base_url}/notifications/{notif_id}/read", headers=headers_a)
assert res.status_code == 200, f"Read notification failed: {res.text}"
print("Notification marked read.")

print("=== 7. TEST MULTI-TENANT USER ISOLATION (USER B) ===")
res = requests.post(f"{base_url}/auth/login", json={"email": "user_b@vajra.ai", "password": "password123"})
token_b = res.json()["access_token"]
headers_b = {"Authorization": f"Bearer {token_b}"}

res_b_mem = requests.get(f"{base_url}/memory/", headers=headers_b)
assert not any(m["id"] == mem_id for m in res_b_mem.json()), "CRITICAL SECURITY LEAK: User B can see User A memory!"
print("Security isolation verified: User B cannot access User A memories.")

res_b_task = requests.get(f"{base_url}/planner/tasks", headers=headers_b)
assert not any(t["id"] == task_id for t in res_b_task.json()), "CRITICAL SECURITY LEAK: User B can see User A task!"
print("Security isolation verified: User B cannot access User A planner tasks.")

print("\n>>> ALL 7 BACKEND RUNTIME TESTS PASSED WITH 100% SUCCESS <<<")
