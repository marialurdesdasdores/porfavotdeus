import os
import openai
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações principais
openai.api_key = os.getenv("OPENAI_API_KEY")
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
UMBLER_ORG_ID = os.getenv("UMBLER_ORG_ID")

# Inicializa o app Flask
app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "API da Floricultura no ar!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Mensagem recebida:", data)

    try:
        # Extrair informações essenciais
        chat_id = data["Payload"]["Content"]["Id"]
        mensagem_usuario = data["Payload"]["Content"]["LastMessage"]["Content"]

        # Gera resposta com ChatGPT
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um atendente simpático de uma floricultura."},
                {"role": "user", "content": mensagem_usuario}
            ]
        )
        resposta_texto = resposta.choices[0].message["content"]
        print("Resposta do ChatGPT:", resposta_texto)

        # Envia a resposta para a Umbler
        url = f"https://app-utalk.umbler.com/api/v1/organization/{UMBLER_ORG_ID}/chat/{chat_id}/reply"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {UMBLER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": resposta_texto
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            print("✅ Mensagem enviada com sucesso para a Umbler!")
        else:
            print(f"❌ Erro ao enviar resposta à Umbler. Status: {response.status_code} | Resposta: {response.text}")

    except Exception as e:
        print(f"❌ Erro no processamento da mensagem: {e}")

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
