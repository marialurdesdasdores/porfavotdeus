from flask import Flask, request, jsonify
import openai
import os
import requests

# Configurações
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

UMBLER_API_URL = "https://app-utalk.umbler.com/api/message/send"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Aplicação rodando"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("Mensagem recebida:", data)

        mensagem = data.get("Payload", {}).get("LastMessage", {}).get("Content")
        chat_id = data.get("Payload", {}).get("LastMessage", {}).get("Chat", {}).get("Id")

        if not mensagem or not chat_id:
            return jsonify({"error": "mensagem ou chat_id não encontrado"}), 400

        resposta = gerar_resposta_chatgpt(mensagem)
        enviar_para_umbler(resposta, chat_id)

        return jsonify({"status": "mensagem enviada"}), 200

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"status": "error", "message": "Erro no servidor"}), 500

def gerar_resposta_chatgpt(mensagem):
    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um assistente útil."},
            {"role": "user", "content": mensagem}
        ],
        max_tokens=150
    )
    return resposta.choices[0].message.content.strip()

def enviar_para_umbler(resposta, chat_id):
    headers = {
        "Authorization": f"Bearer {UMBLER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "chatId": chat_id,
        "content": resposta
    }
    r = requests.post(UMBLER_API_URL, headers=headers, json=payload)
    print("Resposta enviada ao Umbler:", r.status_code, r.text)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
