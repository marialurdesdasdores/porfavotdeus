import os
import openai
import requests
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import time

# Carregar variáveis de ambiente
load_dotenv()

# Configurações da API
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
FROM_PHONE = os.getenv("FROM_PHONE")
UMBLER_SEND_MESSAGE_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

# Configuração do OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializar o Flask
app = Flask(__name__)
CORS(app)

# Configurar logging
logging.basicConfig(filename="webhook_log.log", level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

# Função auxiliar para enviar mensagem com retry
def send_message_with_retry(payload, headers, retries=3, delay=2):
    for attempt in range(retries):
        response = requests.post(UMBLER_SEND_MESSAGE_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response
        logging.warning(f"Tentativa {attempt + 1} falhou: {response.text}")
        time.sleep(delay)
    return response

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        logging.info(f"JSON recebido: {data}")

        # Tenta extrair os dados com segurança
        last_message = data.get("Payload", {}).get("Content", {}).get("LastMessage", {})
        contact_info = data.get("Payload", {}).get("Contact", {})

        message_content = last_message.get("Content", "")
        phone_number = contact_info.get("PhoneNumber", "")

        logging.info(f"Mensagem recebida: {message_content}")
        logging.info(f"Número do cliente: {phone_number}")

        if not message_content or not phone_number:
            logging.error("Mensagem ou número de telefone não encontrados!")
            return jsonify({"error": "Mensagem ou número de telefone não encontrados!"}), 400

        # Histórico de mensagens (simples)
        conversation = [
            {"role": "system", "content": "Você é um assistente inteligente."},
            {"role": "user", "content": message_content}
        ]

        # Resposta do ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation,
            max_tokens=150
        )
        chat_gpt_reply = response.choices[0].message["content"]

        # Enviar a resposta para o Umbler
        payload = {
            "ToPhone": phone_number,
            "FromPhone": FROM_PHONE,
            "OrganizationId": UMBLER_ORG_ID,
            "Message": chat_gpt_reply
        }

        headers = {
            "Authorization": f"Bearer {UMBLER_API_KEY}",
            "Content-Type": "application/json"
        }

        umbler_response = send_message_with_retry(payload, headers)
        logging.info(f"Resposta enviada ao Umbler (status {umbler_response.status_code}): {umbler_response.text}")

        if umbler_response.status_code != 200:
            return jsonify({"error": "Erro ao enviar mensagem para o Umbler."}), 500

        return jsonify({"message": "Mensagem enviada com sucesso!"}), 200

    except Exception as e:
        logging.exception("Erro no webhook")
        return jsonify({"error": f"Erro: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
