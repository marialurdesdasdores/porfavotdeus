import openai
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Configurações
UMBLER_API_KEY = "Token-API-integracaoChatGPT-2025-04-18-2093-05-07--E0B11895AC80831A100AC42DD919006BE896DA5CE0207D6A05CEEF21675F4B14"
OPENAI_API_KEY = "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"

# Definindo chave da API OpenAI
openai.api_key = OPENAI_API_KEY

# URL da API Umbler para enviar mensagens
UMBLER_API_URL = "https://app-utalk.umbler.com/api/message/send"
UMBLER_TALK_WEBHOOK_URL = "https://porfavotdeus.onrender.com/webhook"

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

import openai

def enviar_para_chatgpt(mensagem):
    response = openai.ChatCompletion.create(
    model="gpt-4",  # ou o modelo que você está utilizando
    messages=[
        {"role": "system", "content": "Você é um assistente."},
        {"role": "user", "content": mensagem}
    ]
)

    return response['choices'][0]['message']['content']



def enviar_para_umbler(resposta, chat_id):
    headers = {
        "Authorization": f"Bearer {UMBLER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "chatId": chat_id,
        "content": resposta
    }

    r = requests.post(UMBLER_API_URL, headers=headers, json=payload)
    print("Resposta enviada ao Umbler:", r.status_code, r.text)

    response = requests.post(UMBLER_TALK_WEBHOOK_URL, json=payload, headers=headers)
    if response.status_code == 200:
        print("Mensagem enviada com sucesso para o Umbler Talk.")
    else:
        print(f"Falha ao enviar mensagem. Status: {response.status_code} | Resposta: {response.text}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
