from fastapi import FastAPI, Request
import os
from groq import Groq
from duckduckgo_search import DDGS
from datetime import datetime
import httpx

app = FastAPI()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Simple mémoire
memory = {}

def search_web(query: str):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results: return "Pas de résultats."
            return "\n".join([f"- {r['title']}: {r['body'][:150]}" for r in results])
    except:
        return "Recherche indisponible."

@app.get("/")
def home():
    return {"status": "TechBot CI en ligne", "time": datetime.now().isoformat()}

@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return int(challenge)
    return {"error": "Verification failed"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    try:
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            msg = entry['messages'][0]
            from_number = msg['from']
            text = msg['text']['body']

            # Appel Groq
            search_context = search_web(text) if len(text.split()) > 2 else ""

            prompt = f"""Tu es TechBot CI, assistant IA ivoirien serviable, concis, sympa. Tu parles français.
Contexte web: {search_context}
Utilisateur: {text}
Réponds en 3-4 phrases max, utile, direct."""

            chat = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            reply = chat.choices[0].message.content

            # Envoi WhatsApp
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://graph.facebook.com/v20.0/{os.getenv('WHATSAPP_PHONE_ID')}/messages",
                    headers={"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"},
                    json={"messaging_product": "whatsapp", "to": from_number, "text": {"body": reply}}
                )
    except Exception as e:
        print(f"Erreur: {e}")
    return {"ok": True}
