import openai
from flask import Flask, request, jsonify
import requests

# Configurações
UMBLER_API_KEY = "Token-API-integracaoChatGPT-2025-04-18-2093-05-07--E0B11895AC80831A100AC42DD919006BE896DA5CE0207D6A05CEEF21675F4B14"
OPENAI_API_KEY = "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"

# Nova forma de autenticar
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# URL do webhook (apenas se precisar reencaminhar algo depois)
UMBLER_TALK_WEBHOOK_URL = "https://porfavotdeus.onrender.com/webhook"

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if data:
            print("Mensagem recebida:", data)

            contact_name = data.get('Payload', {}).get('Contact', {}).get('Name', 'Desconhecido')
            last_message = data.get('Payload', {}).get('LastMessage', {}).get('Content', 'Sem mensagem')

            if last_message:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # ou "gpt-4"
                    messages=[
                        {"role": "system", "content": "Você é um assistente útil."},
                        {"role": "user", "content": last_message}
                    ],
                    max_tokens=150
                )

                chatgpt_reply = response.choices[0].message.content.strip()
                print(f"Resposta do ChatGPT: {chatgpt_reply}")

                send_message_to_umbler(contact_name, chatgpt_reply)

            return jsonify({"status": "success", "message": "Mensagem recebida com sucesso!"}), 200

        else:
            return jsonify({"status": "error", "message": "Erro ao processar dados."}), 400

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"status": "error", "message": "Erro no servidor."}), 500

def send_message_to_umbler(contact_name, message):
    payload = {
        "Message": {
            "Content": message,
            "Contact": contact_name
        }
    }

    headers = {
        "Authorization": f"Bearer {UMBLER_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(UMBLER_TALK_WEBHOOK_URL, json=payload, headers=headers)

    if response.status_code == 200:
        print("Mensagem enviada com sucesso para o Umbler Talk.")
    else:
        print(f"Falha ao enviar mensagem. Status: {response.status_code} | Resposta: {response.text}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
