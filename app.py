from flask import Flask, request, jsonify
import requests
import openai

# Chaves diretamente no código (apenas para testes!)
UMBLER_API_KEY = "unclego-2025-04-20-2093-05-08--AC38E58C3CB6B9960A42752253B90D1A26164A345886D83F0EF0210D62170290"
OPENAI_API_KEY = "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"

# Definindo chave da API OpenAI
openai.api_key = OPENAI_API_KEY

# Endpoint da Umbler para envio de mensagens
UMBLER_SEND_MESSAGE_URL = "https://app-utalk.umbler.com/api/v1/messages/simplified/"

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

    return jsonify({"status": "mensagem processada"}), 200

def enviar_para_chatgpt(mensagem):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
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

        r = requests.post(UMBLER_SEND_MESSAGE_URL, headers=headers, json=payload)
        if r.status_code == 200:
            print("Resposta enviada ao Umbler com sucesso.")
        else:
            print(f"Erro ao enviar resposta ao Umbler. Status: {r.status_code} | Resposta: {r.text}")
    except Exception as e:
        print(f"Erro ao enviar para Umbler: {e}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
