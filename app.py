from flask import Flask, request, jsonify
import openai
import requests

app = Flask(__name__)

# SUA CHAVE DA OPENAI
openai.api_key = "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"

# SEU TOKEN DE AUTORIZAÇÃO DO UMBLER TALK
UMBLER_TOKEN = "Token-API-integracaoChatGPT-2025-04-18-2093-05-07--E0B11895AC80831A100AC42DD919006BE896DA5CE0207D6A05CEEF21675F4B14"

# URL da API Umbler para enviar mensagens
UMBLER_API_URL = "https://app-utalk.umbler.com/api/message/send"

@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    data = request.json
    print("Mensagem recebida:", data)

    mensagem = data.get("content")
    chat_id = data.get("chatId")

    if not mensagem or not chat_id:
        return jsonify({"error": "Mensagem ou chatId ausente"}), 400

    # Enviando para o ChatGPT
    resposta = enviar_para_chatgpt(mensagem)

    # Enviando de volta para o Umbler Talk
    enviar_para_umbler(resposta, chat_id)

    return jsonify({"status": "mensagem enviada"}), 200


def enviar_para_chatgpt(mensagem):
    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": mensagem}
        ]
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
