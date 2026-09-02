import os
import requests
import json

kaizen_env = r"C:\Users\hrixo\Downloads\kaizen-phase1 (10)\kaizen\.env"
openrouter_key = None

with open(kaizen_env, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("OPENROUTER_API_KEY="):
            openrouter_key = line.strip().split("=", 1)[1].strip('"\' ')

res = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {openrouter_key}"},
    json={
        "model": "google/gemini-2.5-flash",
        "max_tokens": 300,
        "stream": True,
        "messages": [
            {"role": "system", "content": "You are VAJRA, a personal AI companion."},
            {"role": "user", "content": "What is quantum mechanics?"}
        ]
    },
    stream=True,
    timeout=15
)

print("Stream status:", res.status_code)
collected = []
for line in res.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data: '):
            data_str = decoded[6:]
            if data_str.strip() == '[DONE]':
                print("\n[STREAM COMPLETE]")
                break
            try:
                data = json.loads(data_str)
                delta = data['choices'][0]['delta'].get('content', '')
                collected.append(delta)
                print(delta, end="", flush=True)
            except Exception:
                pass
print(f"\nTotal streamed chunks: {len(collected)}")
