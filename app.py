import os
import requests
import logging
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# Carregar variáveis de ambiente
load_dotenv()

# Configurações da API Umbler
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
FROM_PHONE = os.getenv("FROM_PHONE")
UMBLER_SEND_MESSAGE_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

# Inicializar cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Logging para Render (stdout)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def carregar_prompt_personalizado():
    try:
        with open("prompt_ia.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Erro ao carregar prompt: {e}")
        return "Você é uma atendente virtual educada e prestativa."

def send_message_with_retry(payload, headers, retries=3, delay=2):
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

        content = data.get("Payload", {}).get("Content", {})
        last_message = content.get("LastMessage", {})
        source = last_message.get("Source", "")
        message_type = last_message.get("MessageType", "")
        message_content = last_message.get("Content", "").strip()
        phone_number = content.get("Contact", {}).get("PhoneNumber", "").replace(" ", "").replace("-", "").strip()

        # ⚠️ CORREÇÃO: trata caso File seja None
        file_info = last_message.get("File")
        image_url = file_info.get("Url", "") if isinstance(file_info, dict) else ""

        # Proteção contra loop
        if source != "Contact":
            logging.warning("Mensagem ignorada (não é de um cliente).")
            return jsonify({"status": "ignorada"}), 200

        if not phone_number or (not message_content and not image_url):
            logging.error("Conteúdo ou número ausente.")
            return jsonify({"error": "Dados incompletos"}), 400

        # Carrega o prompt do arquivo
        system_prompt = carregar_prompt_personalizado()

        # Criar mensagem para GPT-4 Vision
        if message_type == "Image" and image_url:
            logging.info(f"Imagem detectada: {image_url}")
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analise essa imagem."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_content}
            ]

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=400
        )
        reply = response.choices[0].message.content.strip()

        # Envia a resposta para o WhatsApp via Umbler
        payload = {
            "ToPhone": phone_number,
            "FromPhone": FROM_PHONE,
            "OrganizationId": UMBLER_ORG_ID,
            "Message": reply
        }
        headers = {
            "Authorization": f"Bearer {UMBLER_API_KEY}",
            "Content-Type": "application/json"
        }

        umbler_response = send_message_with_retry(payload, headers)

        if not umbler_response or umbler_response.status_code != 200:
            logging.error(f"Erro ao enviar resposta. Status: {umbler_response.status_code if umbler_response else 'N/A'}")
            return jsonify({"error": "Falha ao enviar mensagem"}), 500

        logging.info(f"Resposta enviada para {phone_number}: {reply[:60]}...")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.exception("Erro crítico:")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
