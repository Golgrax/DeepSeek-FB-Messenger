from flask import Flask, request
import requests
import hmac
import hashlib

app = Flask(__name__)

# ⚠️ SECURITY WARNING: Never share this file or commit to public repos
# Replace these values with your actual credentials
CONFIG = {
    "DEEPSEEK_API_KEY": "your_deepseek_key_here",
    "FACEBOOK_APP_SECRET": "your_fb_app_secret",
    "PAGE_ACCESS_TOKEN": "your_page_token",
    "VERIFY_TOKEN": "your_custom_verify_token"
}

# API endpoints
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
FB_API_URL = "https://graph.facebook.com/v19.0/me/messages"

def verify_signature(request):
    signature = request.headers.get('X-Hub-Signature-256', '').split('sha256=')[-1]
    payload = request.get_data()
    calculated_signature = hmac.new(
        CONFIG["FACEBOOK_APP_SECRET"].encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, calculated_signature)

def call_deepseek_api(prompt):
    headers = {
        "Authorization": f"Bearer {CONFIG['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek Error: {e}")
        return "I'm having trouble connecting to the AI. Please try again later."

def send_facebook_message(recipient_id, text):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    
    try:
        response = requests.post(
            FB_API_URL,
            json=payload,
            params={'access_token': CONFIG['PAGE_ACCESS_TOKEN']}
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Facebook Send Error: {e}")

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    if request.args.get('hub.mode') == 'subscribe' and \
       request.args.get('hub.verify_token') == CONFIG["VERIFY_TOKEN"]:
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
                if 'message' in messaging_event:
                    sender_id = messaging_event['sender']['id']
                    message_text = messaging_event['message'].get('text', '')
                    if message_text:
                        response_text = call_deepseek_api(message_text)
                        send_facebook_message(sender_id, response_text)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0')
