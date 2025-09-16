"""
Vercel Serverless Function for LINE to Chatwork Bridge
"""
import os
import json
import hashlib
import hmac
import base64
import requests

def verify_signature(body, signature):
    """LINE Webhook署名を検証"""
    channel_secret = os.environ.get('LINE_CHANNEL_SECRET', '')
    if not channel_secret:
        return False

    hash = hmac.new(
        channel_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash).decode('utf-8')
    return signature == expected_signature

def send_to_chatwork(message):
    """Chatworkにメッセージを送信"""
    api_token = os.environ.get('CHATWORK_API_TOKEN', '')
    room_id = os.environ.get('CHATWORK_ROOM_ID', '')

    if not api_token or not room_id:
        print('Chatwork環境変数が設定されていません')
        return False

    url = f'https://api.chatwork.com/v2/rooms/{room_id}/messages'
    headers = {
        'X-ChatWorkToken': api_token,
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

def handler(request, response):
    """Vercel Serverless Function Handler"""
    # GETリクエスト（ヘルスチェック）
    if request.method == 'GET':
        response.status_code = 200
        response.headers['Content-Type'] = 'text/plain'
        return 'LINE to Chatwork Bridge is running on Vercel'

    # POSTリクエスト処理
    if request.method != 'POST':
        response.status_code = 405
        return 'Method Not Allowed'

    # 署名検証
    signature = request.headers.get('x-line-signature', '')
    body = request.body

    if not verify_signature(body, signature):
        response.status_code = 400
        return 'Invalid signature'

    # JSONをパース
    try:
        events = json.loads(body).get('events', [])
    except json.JSONDecodeError:
        response.status_code = 400
        return 'Invalid JSON'

    # イベント処理
    for event in events:
        if event['type'] == 'message':
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

    # 成功レスポンス
    response.status_code = 200
    return 'OK'