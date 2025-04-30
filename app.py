import os
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

# Inicializar cliente OpenAI (sem 'proxies')
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Configuração da Umbler
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")
FROM_PHONE = os.getenv("FROM_PHONE")
UMBLER_SEND_MESSAGE_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

# Setup Flask
app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Carregar prompt customizado
with open("promt IA.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()

# Controle para evitar loop de respostas
ultima_resposta_por_contato = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logging.info("Payload bruto recebido:\n%s", data)

        content = data.get("Payload", {}).get("Content")
        contact = content.get("Contact") if content else None
        last_message = content.get("LastMessage") if content else None

        # Verifica se é imagem ou texto
        message_content = last_message.get("Content") if last_message else None
        file_info = last_message.get("File") if last_message else None
        phone_number = contact.get("PhoneNumber") if contact else None

        if not phone_number:
            logging.error("Conteúdo ou número ausente.")
            return ("Conteúdo ou número ausente.", 400)

        # Verifica se é uma imagem com URL
        if file_info and file_info.get("Url"):
            image_url = file_info.get("Url")
            logging.info("🖼️ Cliente enviou imagem: %s", image_url)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Descreva o que você vê nesta imagem."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ]
            )
            reply = response.choices[0].message.content

        elif message_content:
            logging.info("💬 Cliente enviou texto: %s", message_content)

            # Anti-loop: se for igual à última resposta, não responde
            if ultima_resposta_por_contato.get(phone_number) == message_content.strip():
                logging.warning("⚠️ Detecção de loop. Ignorando mensagem.")
                return ("Loop detectado.", 200)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message_content.strip()}
                ]
            )
            reply = response.choices[0].message.content
            ultima_resposta_por_contato[phone_number] = reply.strip()

        else:
            logging.error("❌ Nenhuma mensagem processável encontrada.")
            return ("Nada para processar.", 400)

        # Enviar resposta via Umbler
        response_data = {
            "To": phone_number,
            "From": FROM_PHONE,
            "Text": reply.strip()
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": UMBLER_API_KEY,
            "x-org-id": UMBLER_ORG_ID
        }
        res = requests.post(UMBLER_SEND_MESSAGE_URL, json=response_data, headers=headers)
        logging.info("Resposta enviada para %s: %s", phone_number, reply)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.exception("Erro crítico:")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")