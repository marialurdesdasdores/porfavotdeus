import os
import openai
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações da API
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
FROM_PHONE = os.getenv("FROM_PHONE")  # Seu número autorizado pelo Umbler
UMBLER_SEND_MESSAGE_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

# Configuração do OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializar o Flask
app = Flask(__name__)
CORS(app)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        # Extração de mensagem e telefone
        message_content = data.get("Payload", {}).get("Content", {}).get("LastMessage", {}).get("Content", "")
        phone_number = data.get("Payload", {}).get("Contact", {}).get("PhoneNumber", "")

        if not message_content or not phone_number:
            return jsonify({"error": "Mensagem ou número de telefone não encontrados!"}), 400

        # Chamada correta para ChatCompletion (modelo gpt-3.5-turbo)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é uma atendente virtual da Amanda Floricultura."},
                {"role": "user", "content": message_content}
            ],
            max_tokens=150,
            temperature=0.7
        )
        chat_gpt_reply = response.choices[0].message.content.strip()

        # Corpo da requisição para o Umbler
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

        umbler_response = requests.post(UMBLER_SEND_MESSAGE_URL, json=payload, headers=headers)

        if umbler_response.status_code != 200:
            return jsonify({
                "error": f"Erro ao enviar mensagem para o Umbler.",
                "status_code": umbler_response.status_code,
                "response": umbler_response.text
            }), 500

        return jsonify({"message": "Mensagem enviada com sucesso!"}), 200

    except Exception as e:
        return jsonify({"error": f"Erro: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
