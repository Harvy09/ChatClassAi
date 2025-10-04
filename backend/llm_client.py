import os, requests
from dotenv import load_dotenv

load_dotenv()

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://api.cerebras.ai/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY")

def query_llm(messages, max_tokens=400, temperature=0.7):
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3.1-8b",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    response = requests.post(LLM_ENDPOINT, headers=headers, json=payload)
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return f"⚠️ Error: {data}"
