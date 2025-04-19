from flask import Flask, request, jsonify
import openai
import requests
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
UMBLER_TOKEN = os.getenv("UMBLER_TOKEN")

# URL da API Umbler para enviar mensagens
UMBLER_API_URL = "https://app-utalk.umbler.com/api/message/send"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Aplicação rodando"}), 200

@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    data = request.json
    print("Mensagem recebida:", data)

    try:
        mensagem = data['Payload']['Content']['LastMessage']['Content']
        chat_id = data['Payload']['Content']['LastMessage']['Chat']['Id']
    except (KeyError, TypeError) as e:
        print("Erro ao acessar mensagem ou chat_id:", e)
        return jsonify({"error": "mensagem ou chat_id não encontrado"}), 400

    resposta = enviar_para_chatgpt(mensagem)
    enviar_para_umbler(resposta, chat_id)

    return jsonify({"status": "mensagem enviada"}), 200



def enviar_para_chatgpt(mensagem):
    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": mensagem}]
    )
    return resposta.choices[0].message.content.strip()


def enviar_para_umbler(resposta, chat_id):
    headers = {
        "Authorization": f"Bearer {UMBLER_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "chatId": chat_id,
        "content": resposta
    }
    r = requests.post(UMBLER_API_URL, headers=headers, json=payload)
    print("Resposta enviada ao Umbler:", r.status_code, r.text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
