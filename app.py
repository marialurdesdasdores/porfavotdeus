import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import uuid
import logging

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
umbler_token = os.getenv("UMBLER_TOKEN")  # Token da API Umbler
client = OpenAI(api_key=openai_api_key)

# Logging
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=["GET"])
def home():
    return "✅ API do bot está rodando com sucesso!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        logging.info("Mensagem recebida: %s", data)

        mensagem = data.get("Payload", {}).get("Content", {}).get("LastMessage", {}).get("Content", "")
        telefone = data.get("Payload", {}).get("Content", {}).get("Contact", {}).get("PhoneNumber", "")
        
        if not mensagem or not telefone:
            return jsonify({"error": "Mensagem ou telefone não encontrados"}), 400

        # Gerar resposta com ChatGPT
        resposta = gerar_resposta(mensagem)
        logging.info("Resposta do ChatGPT: %s", resposta)

        # Enviar a resposta de volta pelo Umbler
        enviar_para_umbler(telefone, resposta)

        return jsonify({"status": "mensagem processada"}), 200

    except Exception as e:
        logging.exception("Erro ao processar webhook")
        return jsonify({"error": str(e)}), 500

def gerar_resposta(mensagem_usuario):
    resposta = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é uma atendente virtual de uma floricultura. Atenda com simpatia e ofereça sugestões personalizadas."},
            {"role": "user", "content": mensagem_usuario},
        ]
    )
    return resposta.choices[0].message.content.strip()

def enviar_para_umbler(numero, mensagem):
    try:
        endpoint = f"https://v1.utalk.chat/send/{umbler_token}"

        payload = {
            "cmd": "chat",
            "id": str(uuid.uuid4()),
            "to": f"{numero.replace('+', '').replace(' ', '')}@c.us",
            "msg": mensagem
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(endpoint, json=payload, headers=headers)

        if response.status_code != 200:
            logging.error("Erro ao enviar para Umbler: %s | Resposta: %s", response.status_code, response.text)
        else:
            logging.info("Mensagem enviada com sucesso para Umbler.")

    except Exception as e:
        logging.exception("Erro ao enviar resposta à Umbler")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
