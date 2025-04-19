from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import openai

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Definindo chave da API OpenAI
openai.api_key = OPENAI_API_KEY

# URL da API Umbler para enviar mensagens
UMBLER_API_URL = "https://app-utalk.umbler.com/api/message/send"
UMBLER_TALK_WEBHOOK_URL = "https://porfavotdeus.onrender.com/webhook"

app = Flask(__name__)

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
    if resposta:
        enviar_para_umbler(resposta, chat_id)
    else:
        print("Erro ao obter resposta do ChatGPT. Mensagem não enviada.")

    return jsonify({"status": "mensagem enviada"}), 200

def enviar_para_chatgpt(mensagem):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # ou o modelo que você está utilizando
            messages=[
                {"role": "system", "content": "Você é um assistente."},
                {"role": "user", "content": mensagem}
            ]
        )
        resposta_chatgpt = response['choices'][0]['message']['content']
        print("Resposta do ChatGPT:", resposta_chatgpt)
        return resposta_chatgpt
    except Exception as e:
        print(f"Erro ao comunicar com o ChatGPT: {e}")
        return None

def enviar_para_umbler(resposta, chat_id):
    try:
        headers = {
            "Authorization": f"Bearer {UMBLER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "chatId": chat_id,
            "content": resposta
        }

        r = requests.post(UMBLER_API_URL, headers=headers, json=payload)
        if r.status_code == 200:
            print("Resposta enviada ao Umbler com sucesso.")
        else:
            print(f"Erro ao enviar resposta ao Umbler. Status: {r.status_code} | Resposta: {r.text}")

        response = requests.post(UMBLER_TALK_WEBHOOK_URL, json=payload, headers=headers)
        if response.status_code == 200:
            print("Mensagem enviada com sucesso para o Umbler Talk.")
        else:
            print(f"Falha ao enviar mensagem para o Umbler Talk. Status: {response.status_code} | Resposta: {response.text}")
    except Exception as e:
        print(f"Erro ao enviar para Umbler: {e}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
