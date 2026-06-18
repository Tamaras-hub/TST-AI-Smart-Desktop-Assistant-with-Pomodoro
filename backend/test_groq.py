import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY", "").strip()
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODELO = "llama-3.3-70b-versatile"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODELO,
    "messages": [
        {"role": "user", "content": "Hola, responde brevemente con un JSON: {\"saludo\": \"hola\"}"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

try:
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
