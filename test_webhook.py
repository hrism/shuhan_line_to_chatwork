#!/usr/bin/env python3
import json
import requests
import hmac
import hashlib
import base64

# LINE Webhook署名を生成する関数
def generate_signature(body, channel_secret):
    hash = hmac.new(
        channel_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(hash).decode('utf-8')
    return signature

# テスト用のLINEメッセージ
test_event = {
    "events": [
        {
            "type": "message",
            "message": {
                "type": "text",
                "text": "テストメッセージです"
            },
            "source": {
                "type": "user",
                "userId": "U2ebd50d61b186e2640dadf7509a48f1e"
            }
        }
    ]
}

# JSONに変換
body = json.dumps(test_event)

# 署名生成
channel_secret = '176c32df1bd77d1f85b8e0c7aa167849'
signature = generate_signature(body, channel_secret)

# Webhookにリクエスト送信
url = 'http://localhost:5001/webhook'
headers = {
    'X-Line-Signature': signature,
    'Content-Type': 'application/json'
}

try:
    response = requests.post(url, headers=headers, data=body)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")