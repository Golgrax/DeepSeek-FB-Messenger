from flask import Flask, request, jsonify
import requests
import os
import hmac
import hashlib

app = Flask(__name__)

# Configuration - Will set these in PythonAnywhere dashboard
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# API endpoints
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
FB_API_URL = "https://graph.facebook.com/v19.0/me/messages"

def verify_signature(request):
    signature = request.headers.get('X-Hub-Signature-256', '').split('sha256=')[-1]
    payload = request.get_data()
    calculated_signature = hmac.new(
        FACEBOOK_APP_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, calculated_signature)

def call_deepseek_api(prompt):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    
    try:
        response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek API Error: {e}")
        return "I'm having trouble connecting to the AI. Please try again later."

def send_facebook_message(recipient_id, text):
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    params = {'access_token': PAGE_ACCESS_TOKEN}
    
    try:
        response = requests.post(FB_API_URL, json=payload, params=params)
        response.raise_for_status()
    except Exception as e:
        print(f"Facebook API Error: {e}")

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def handle_messages():
    if not verify_signature(request):
        return "Invalid signature", 403
    
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            for messaging_event in entry.get('messaging', []):
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    message_text = messaging_event['message'].get('text', '')
                    if message_text:
                        response_text = call_deepseek_api(message_text)
                        send_facebook_message(sender_id, response_text)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0')
