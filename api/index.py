from http.server import BaseHTTPRequestHandler
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
        body,
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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GETリクエスト処理（ヘルスチェック）"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'LINE to Chatwork Bridge is running on Vercel')

    def do_POST(self):
        """POSTリクエスト処理"""
        # 署名検証
        signature = self.headers.get('X-Line-Signature', '')
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if not verify_signature(body, signature):
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid signature')
            return

        # JSONをパース
        try:
            body_json = json.loads(body)
            events = body_json.get('events', [])
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return

        # イベント処理
        for event in events:
            event_type = event.get('type', 'unknown')

            # メッセージイベントの処理
            if event_type == 'message':
                message = event.get('message', {})
                message_type = message.get('type', 'N/A')

                if message_type == 'text':
                    text = message.get('text', '')
                    chatwork_message = f"[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]{text}[/info]"
                elif message_type == 'image':
                    chatwork_message = "[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]画像が送信されました[/info]"
                elif message_type == 'sticker':
                    chatwork_message = "[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]スタンプが送信されました[/info]"
                elif message_type == 'video':
                    chatwork_message = "[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]動画が送信されました[/info]"
                elif message_type == 'audio':
                    chatwork_message = "[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]音声が送信されました[/info]"
                elif message_type == 'file':
                    file_name = message.get('fileName', 'ファイル')
                    chatwork_message = f"[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]ファイルが送信されました: {file_name}[/info]"
                elif message_type == 'location':
                    title = message.get('title', '位置情報')
                    chatwork_message = f"[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]位置情報が送信されました: {title}[/info]"
                else:
                    chatwork_message = f"[info][title]ストックラボ（酒販）LINEの新規メッセージ[/title]{message_type}タイプのメッセージを受信[/info]"

                # Chatworkに送信
                send_to_chatwork(chatwork_message)

        # 成功レスポンス
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')