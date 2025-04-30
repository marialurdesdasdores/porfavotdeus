import os
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# Carrega variáveis de ambiente
load_dotenv()

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Inicializa Flask
app = Flask(__name__)
CORS(app)

# Inicializa cliente OpenAI (sem proxies)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuração Umbler
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")
FROM_PHONE = os.getenv("FROM_PHONE")
UMBLER_SEND_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

# Carrega prompt base
with open("promt IA.txt", "r", encoding="utf-8") as f:
    BASE_PROMPT = f.read().strip()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logging.info("Payload bruto recebido:\n%s", data)

        content = data.get("Payload", {}).get("Content", {})
        contact = content.get("Contact", {})
        phone_number = contact.get("PhoneNumber")
        last_message = content.get("LastMessage") or content.get("Message")

        if not last_message or not phone_number:
            logging.error("Conteúdo ou número ausente.")
            return jsonify({"error": "Conteúdo ou número do cliente ausente."}), 400

        message_type = last_message.get("MessageType", "Text")
        message_text = last_message.get("Content")
        file_info = last_message.get("File")

        if message_type == "Image" and file_info:
            image_url = file_info.get("Url")
            if not image_url:
                logging.warning("Imagem recebida, mas sem URL válida.")
                return jsonify({"status": "sem URL de imagem"}), 400

            logging.info("📷 Imagem recebida: %s", image_url)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": BASE_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Por favor, analise esta imagem."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ]
            )
            reply = response.choices[0].message.content.strip()

        elif message_text:
            logging.info("🖊️ Cliente enviou texto: %s", message_text)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": BASE_PROMPT},
                    {"role": "user", "content": message_text}
                ]
            )
            reply = response.choices[0].message.content.strip()
        else:
            logging.warning("Nenhum conteúdo processável.")
            return jsonify({"status": "sem conteúdo válido"}), 400

        payload = {
            "PhoneNumber": phone_number,
            "Message": reply,
            "FromPhoneNumber": FROM_PHONE
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": UMBLER_API_KEY,
            "X-ORG-ID": UMBLER_ORG_ID
        }

        response = requests.post(UMBLER_SEND_URL, json=payload, headers=headers)
        logging.info("Resposta enviada para %s: %s", phone_number, reply)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.exception("Erro crítico:")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")