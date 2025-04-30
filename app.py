import os
import openai
import requests
import logging
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import time

# Carregar variáveis de ambiente
load_dotenv()

# Configurações da API Umbler
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
logging.basicConfig(
    filename="webhook.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def send_message_with_retry(payload, headers, retries=3, delay=2):
    """Tenta enviar mensagem até 3 vezes em caso de falha."""
    for attempt in range(retries):
        try:
            response = requests.post(
                UMBLER_SEND_MESSAGE_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response
            logging.error(f"Tentativa {attempt + 1} falhou. Status: {response.status_code}. Resposta: {response.text}")
        except Exception as e:
            logging.error(f"Erro na tentativa {attempt + 1}: {str(e)}")
        time.sleep(delay)
    return None

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        logging.info("Payload bruto recebido:\n" + json.dumps(data, indent=2, ensure_ascii=False))

        # Extrai mensagem e número
        last_message = data.get("Payload", {}).get("Content", {}).get("LastMessage", {})
        contact_info = data.get("Payload", {}).get("Contact", {})

        message_content = last_message.get("Content", "").strip()
        phone_number = contact_info.get("PhoneNumber", "").replace(" ", "").replace("-", "").strip()

        if not message_content or not phone_number:
            logging.error("Mensagem ou número do cliente ausente no payload.")
            return jsonify({"error": "Dados incompletos no webhook."}), 400

        # Cria conversa com GPT
        conversation = [
            {"role": "system", "content": "Você é um atendente virtual simpático, prestativo e responde em português."},
            {"role": "user", "content": message_content}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation,
            max_tokens=200
        )
        chat_gpt_reply = response.choices[0].message["content"].strip()

        # Prepara envio para Umbler
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

        if not umbler_response or umbler_response.status_code != 200:
            logging.error(f"Falha ao enviar mensagem. Status: {umbler_response.status_code if umbler_response else 'N/A'}")
            logging.error(f"Headers: {umbler_response.headers if umbler_response else 'N/A'}")
            logging.error(f"Resposta: {umbler_response.text if umbler_response else 'N/A'}")
            return jsonify({"error": "Falha ao enviar mensagem para o Umbler."}), 500

        logging.info(f"Resposta enviada para {phone_number}: {chat_gpt_reply[:60]}...")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.exception("Erro crítico no webhook:")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
