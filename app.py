import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import requests

# Carrega variáveis de ambiente do .env
load_dotenv()

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Inicializa o cliente da OpenAI sem proxies
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Flask setup
app = Flask(__name__)
CORS(app)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logging.info("Payload bruto recebido:\n%s", data)

        payload = data.get("Payload", {})
        content = payload.get("Content", {})
        contact = payload.get("Contact", {})
        phone_number = contact.get("PhoneNumber", "")

        last_message = content.get("LastMessage") or content.get("Message")
        message_type = last_message.get("MessageType") if last_message else None
        message_content = last_message.get("Content") if last_message else None
        file_info = last_message.get("File") if last_message else None

        if not phone_number:
            logging.error("Telefone ausente no payload.")
            return jsonify({"error": "Telefone ausente."}), 400

        if message_type == "Image" and file_info:
            image_url = file_info.get("Url")
            if not image_url:
                logging.error("URL da imagem ausente.")
                return jsonify({"error": "URL da imagem ausente."}), 400

            logging.info("📷 Cliente enviou imagem: %s", image_url)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é uma assistente virtual e deve analisar imagens enviadas pelos clientes e responder com base nelas."},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]},
                ],
                max_tokens=500
            )

            resposta = response.choices[0].message.content.strip()

        elif message_type == "Text" and message_content:
            logging.info("🗣️ Cliente enviou texto: %s", message_content)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": os.getenv("IA_PROMPT", "Você é uma assistente virtual."),},
                    {"role": "user", "content": message_content.strip()},
                ],
                max_tokens=500
            )

            resposta = response.choices[0].message.content.strip()
        else:
            logging.error("Conteúdo ou tipo de mensagem inválido.")
            return jsonify({"error": "Conteúdo ou tipo de mensagem inválido."}), 400

        logging.info("📢 Resposta enviada para %s: %s", phone_number, resposta[:100])
        return jsonify({"status": "success"})

    except Exception as e:
        logging.error("Erro crítico:", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
