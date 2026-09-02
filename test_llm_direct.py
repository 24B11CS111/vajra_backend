import os
import requests

kaizen_env = r"C:\Users\hrixo\Downloads\kaizen-phase1 (10)\kaizen\.env"
openrouter_key = None

with open(kaizen_env, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("OPENROUTER_API_KEY="):
            openrouter_key = line.strip().split("=", 1)[1].strip('"\' ')

models = [
    "google/gemini-2.5-flash",
    "google/gemini-2.0-flash-001",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-72b-instruct"
]

for model in models:
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {openrouter_key}"},
        json={
            "model": model,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": "You are VAJRA, a personal AI companion."},
                {"role": "user", "content": "Hello VAJRA"}
            ]
        },
        timeout=10
    )
    print(f"Model: {model} -> Status: {res.status_code}")
    if res.status_code == 200:
        print("  Answer:", res.json()["choices"][0]["message"]["content"][:120])
