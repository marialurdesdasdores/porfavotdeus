from flask import Flask, request, jsonify
import requests
import os
import openai
from dotenv import load_dotenv
import logging

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Recupera as chaves da OpenAI e Umbler
UMBLER_API_KEY = os.getenv("UMBLER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Verifica se as chaves foram carregadas corretamente
if not UMBLER_API_KEY or not OPENAI_API_KEY:
    raise ValueError("Erro: UMBLER_API_KEY ou OPENAI_API_KEY não foram carregadas. Verifique seu .env e as variáveis no Render.")

# Configura a chave da OpenAI
openai.api_key = OPENAI_API_KEY

# URL da Umbler para envio de mensagens
UMBLER_SEND_MESSAGE_URL = "https://api.utalk.com.br/v1/messages"

# Inicializa a aplicação Flask
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Aplicação rodando"}), 200

@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    data = request.json
    logging.info("Mensagem recebida: %s", data)

    try:
        mensagem = data['Payload']['Content']['LastMessage']['Content']
        chat_id = data['Payload']['Content']['LastMessage']['Chat']['Id']
        from_phone = data['Payload']['Content']['Channel']['PhoneNumber']
        to_phone = data['Payload']['Content']['Contact']['PhoneNumber']
    except (KeyError, TypeError) as e:
        logging.error("Erro ao acessar mensagem ou chat_id: %s", e)
        return jsonify({"error": "mensagem ou chat_id não encontrado"}), 400

    resposta = enviar_para_chatgpt(mensagem)
    if resposta:
        enviar_para_umbler(resposta, chat_id, from_phone, to_phone)
    else:
        logging.error("Erro ao obter resposta do ChatGPT. Mensagem não enviada.")

    return jsonify({"status": "mensagem processada"}), 200

def enviar_para_chatgpt(mensagem):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente virtual simpático e prestativo de uma floricultura. Sempre tente entender o pedido do cliente e sugerir os melhores produtos disponíveis."
                },
                {
                    "role": "user",
                    "content": mensagem
                }
            ]
        )
        resposta_chatgpt = response['choices'][0]['message']['content']
        logging.info("Resposta do ChatGPT: %s", resposta_chatgpt)
        return resposta_chatgpt
    except Exception as e:
        logging.error("Erro ao comunicar com o ChatGPT: %s", e)
        return None

def enviar_para_umbler(resposta, chat_id, from_phone, to_phone):
    try:
        headers = {
            "Authorization": f"Bearer {UMBLER_API_KEY}",
            "Content-Type": "application/json"
        }

        # ESTE É O FORMATO QUE A API DA UMBLER ESPERA:
        payload = {
            "model": {
                "chatId": chat_id,
                "fromPhone": from_phone,
                "toPhone": to_phone,
                "message": {
                    "type": "Text",
                    "content": resposta,
                    "quotedMessageId": None
                }
            }
        }

        r = requests.post(UMBLER_SEND_MESSAGE_URL, headers=headers, json=payload)

        if r.status_code == 200:
            logging.info("Resposta enviada à Umbler com sucesso.")
        else:
            logging.error("Erro ao enviar resposta à Umbler. Status: %s | Resposta: %s", r.status_code, r.text)
    except Exception as e:
        logging.error("Erro ao enviar para Umbler: %s", e)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
