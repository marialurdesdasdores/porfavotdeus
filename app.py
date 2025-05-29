import os
import requests
import logging
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import openai

# Carrega variáveis do .env
load_dotenv()

# Configurações da Umbler
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
FROM_PHONE = os.getenv("FROM_PHONE")
UMBLER_SEND_MESSAGE_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

# Configuração da API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializa Flask
app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def carregar_prompt():
    try:
        with open("prompt_ia.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Você é uma atendente virtual de uma floricultura. Seja educada e útil."

def carregar_catalogo():
    try:
        with open("catalogo_produtos.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def contem_palavra_chave(texto):
    texto = texto.lower()
    palavras = ["produto", "produtos", "opções", "flores", "cestas", "presentes", "catálogo", "arranjos", "tem o quê", "tem o que", "tem algo"]
    return any(p in texto for p in palavras)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        logging.info("Payload bruto recebido:\n" + json.dumps(data, indent=2, ensure_ascii=False))

        content = data.get("Payload", {}).get("Content", {})
        last_message = content.get("LastMessage", {})
        source = last_message.get("Source", "")
        message_type = last_message.get("MessageType", "") or content.get("Message", {}).get("MessageType", "")
        raw_content = last_message.get("Content")
        message_content = raw_content.strip() if isinstance(raw_content, str) else ""

        phone_number = content.get("Contact", {}).get("PhoneNumber", "").replace(" ", "").replace("-", "").strip()
        attachment_url = last_message.get("Attachment", {}).get("Url", "")
        tem_imagem = bool(attachment_url)

        if source != "Contact":
            logging.warning("Mensagem ignorada (não é de um cliente).")
            return jsonify({"status": "ignorada"}), 200

        if not phone_number or (not message_content and not tem_imagem):
            logging.error("Conteúdo ou número ausente.")
            return jsonify({"error": "Dados incompletos"}), 400

        prompt_base = carregar_prompt()
        catalogo = carregar_catalogo()

        if contem_palavra_chave(message_content):
            system_prompt = prompt_base + "\n\n📦 Catálogo de produtos:\n" + catalogo
        else:
            system_prompt = prompt_base

        # Criação das mensagens com ou sem imagem
        if tem_imagem:
            logging.info(f"🖼️ Cliente enviou uma imagem: {attachment_url}")
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message_content or "Descreva a imagem."},
                        {"type": "image_url", "image_url": {"url": attachment_url}}
                    ]
                }
            ]
        else:
            logging.info(f"💬 Cliente enviou texto: {message_content}")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_content}
            ]

        # Chamada para a OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=400
        )
        reply = response.choices[0].message["content"].strip()

        # Enviar resposta para o WhatsApp via Umbler
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

        r = requests.post(UMBLER_SEND_MESSAGE_URL, json=payload, headers=headers)
        logging.info(f"✅ Resposta enviada para {phone_number}: {reply[:60]}...")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.exception("Erro crítico:")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
