import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


pasta_projeto = Path(__file__).resolve().parent
load_dotenv(pasta_projeto / ".env")

chave = os.getenv("GEMINI_API_KEY")

if not chave:
    raise SystemExit("Chave ausente. Confira o arquivo .env.")

client = genai.Client(api_key=chave)

print("Consultando os modelos disponíveis...\n")

for modelo in client.models.list():
    acoes = modelo.supported_actions or []

    if "generateContent" in acoes and "flash" in modelo.name.lower():
        print(modelo.name)

print("\nConsulta concluída.")