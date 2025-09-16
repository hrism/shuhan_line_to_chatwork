#!/usr/bin/env python3
import os
import json
import hashlib
import hmac
import base64
from flask import Flask, request, abort
import requests

app = Flask(__name__)

# LINE設定
LINE_CHANNEL_SECRET = '176c32df1bd77d1f85b8e0c7aa167849'
LINE_CHANNEL_ACCESS_TOKEN = 'lMjxvYYsIR10PKYFOm5cyT9sTb43jvaMlzZCTILcMF6XncnVYQS9LABVFPPU1tsLEQ1rm4rY4NGP8En9QRcMFPJTNC8/p3dbt1rVC1T0UkFEJMJNqL+ce9Qodd5z/lBK273pL8c0AnCFyppVODzzEgdB04t89/1O/w1cDnyilFU='

# Chatwork設定
CHATWORK_API_TOKEN = '4beb33e52c5f6ea0921888118cb77f9a'
CHATWORK_ROOM_ID = '351472633'

def verify_signature(body, signature):
    """LINE Webhook署名を検証"""
    hash = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash).decode('utf-8')
    return signature == expected_signature

def send_to_chatwork(message):
    """Chatworkにメッセージを送信"""
    url = f'https://api.chatwork.com/v2/rooms/{CHATWORK_ROOM_ID}/messages'
    headers = {
        'X-ChatWorkToken': CHATWORK_API_TOKEN,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'body': message}

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f'Chatwork送信エラー: {e}')
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    """LINE Webhookエンドポイント"""
    # 署名検証
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    if not verify_signature(body, signature):
        abort(400)

    # JSONをパース
    try:
        events = json.loads(body).get('events', [])
    except json.JSONDecodeError:
        abort(400)

    # イベント処理
    for event in events:
        if event['type'] == 'message':
            # メッセージイベントの処理
            message_type = event['message']['type']
            user_id = event.get('source', {}).get('userId', 'Unknown')

            if message_type == 'text':
                text = event['message']['text']
                chatwork_message = f'[info][title]LINEメッセージ受信[/title]メッセージ: {text}\nユーザーID: {user_id}[/info]'
            elif message_type == 'image':
                chatwork_message = f'[info][title]LINEメッセージ受信[/title]画像が送信されました\nユーザーID: {user_id}[/info]'
            elif message_type == 'sticker':
                chatwork_message = f'[info][title]LINEメッセージ受信[/title]スタンプが送信されました\nユーザーID: {user_id}[/info]'
            else:
                chatwork_message = f'[info][title]LINEメッセージ受信[/title]{message_type}タイプのメッセージを受信\nユーザーID: {user_id}[/info]'

            # Chatworkに送信
            send_to_chatwork(chatwork_message)

    return 'OK', 200

@app.route('/', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return 'LINE to Chatwork Bridge is running', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)