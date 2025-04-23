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
FROM_PHONE = os.getenv("FROM_PHONE")
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
        print("✅ JSON recebido no webhook:", data)  # Log da entrada

        # Tenta extrair os dados com segurança
        message_content = data.get("Payload", {}).get("Content", {}).get("LastMessage", {}).get("Content", "")
        phone_number = data.get("Payload", {}).get("Contact", {}).get("PhoneNumber", "")

        print(f"📩 Mensagem recebida: {message_content}")
        print(f"📞 Número do cliente: {phone_number}")

        if not message_content or not phone_number:
            print("⚠️ Mensagem ou número de telefone não encontrados!")
            return jsonify({"error": "Mensagem ou número de telefone não encontrados!"}), 400

        # Resposta do ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message_content}],
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

        umbler_response = requests.post(UMBLER_SEND_MESSAGE_URL, json=payload, headers=headers)
        print(f"📤 Resposta enviada ao Umbler (status {umbler_response.status_code}): {umbler_response.text}")

        if umbler_response.status_code != 200:
            return jsonify({"error": "Erro ao enviar mensagem para o Umbler."}), 500

        return jsonify({"message": "Mensagem enviada com sucesso!"}), 200

    except Exception as e:
        print(f"❌ Erro no webhook: {str(e)}")
        return jsonify({"error": f"Erro: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
