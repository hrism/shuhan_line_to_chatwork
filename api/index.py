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
            # イベント全体のデータを収集
            event_type = event.get('type', 'unknown')
            event_id = event.get('webhookEventId', 'N/A')
            timestamp = event.get('timestamp', 'N/A')
            mode = event.get('mode', 'N/A')
            reply_token = event.get('replyToken', 'N/A')

            # ソース情報
            source = event.get('source', {})
            source_type = source.get('type', 'N/A')
            user_id = source.get('userId', 'N/A')
            group_id = source.get('groupId', 'N/A')
            room_id = source.get('roomId', 'N/A')

            # メッセージイベントの処理
            if event_type == 'message':
                message = event.get('message', {})
                message_id = message.get('id', 'N/A')
                message_type = message.get('type', 'N/A')
                quoted_message_id = message.get('quotedMessageId', 'N/A')

                # メッセージタイプ別の詳細情報
                detail_info = []

                if message_type == 'text':
                    text = message.get('text', '')
                    detail_info.append(f"テキスト: {text}")

                    # メンション情報があれば追加
                    if 'mention' in message:
                        mentions = message['mention'].get('mentionees', [])
                        for mention in mentions:
                            detail_info.append(f"メンション: @{mention.get('userId', 'N/A')} (インデックス: {mention.get('index', 'N/A')}, 長さ: {mention.get('length', 'N/A')})")

                    # 絵文字情報があれば追加
                    if 'emojis' in message:
                        for emoji in message['emojis']:
                            detail_info.append(f"絵文字: ID={emoji.get('emojiId', 'N/A')}, インデックス={emoji.get('index', 'N/A')}")

                elif message_type == 'image':
                    content_provider = message.get('contentProvider', {})
                    provider_type = content_provider.get('type', 'N/A')
                    detail_info.append(f"画像プロバイダー: {provider_type}")
                    if provider_type == 'external':
                        detail_info.append(f"画像URL: {content_provider.get('originalContentUrl', 'N/A')}")
                        detail_info.append(f"プレビューURL: {content_provider.get('previewImageUrl', 'N/A')}")
                    detail_info.append(f"画像セット: {message.get('imageSet', 'N/A')}")

                elif message_type == 'video':
                    duration = message.get('duration', 'N/A')
                    detail_info.append(f"動画長さ: {duration}ms")
                    content_provider = message.get('contentProvider', {})
                    detail_info.append(f"動画プロバイダー: {content_provider.get('type', 'N/A')}")

                elif message_type == 'audio':
                    duration = message.get('duration', 'N/A')
                    detail_info.append(f"音声長さ: {duration}ms")
                    content_provider = message.get('contentProvider', {})
                    detail_info.append(f"音声プロバイダー: {content_provider.get('type', 'N/A')}")

                elif message_type == 'file':
                    file_name = message.get('fileName', 'N/A')
                    file_size = message.get('fileSize', 'N/A')
                    detail_info.append(f"ファイル名: {file_name}")
                    detail_info.append(f"ファイルサイズ: {file_size}バイト")

                elif message_type == 'location':
                    title = message.get('title', 'N/A')
                    address = message.get('address', 'N/A')
                    latitude = message.get('latitude', 'N/A')
                    longitude = message.get('longitude', 'N/A')
                    detail_info.append(f"場所: {title}")
                    detail_info.append(f"住所: {address}")
                    detail_info.append(f"座標: ({latitude}, {longitude})")

                elif message_type == 'sticker':
                    package_id = message.get('packageId', 'N/A')
                    sticker_id = message.get('stickerId', 'N/A')
                    sticker_resource_type = message.get('stickerResourceType', 'N/A')
                    keywords = message.get('keywords', [])
                    detail_info.append(f"パッケージID: {package_id}")
                    detail_info.append(f"スタンプID: {sticker_id}")
                    detail_info.append(f"リソースタイプ: {sticker_resource_type}")
                    if keywords:
                        detail_info.append(f"キーワード: {', '.join(keywords)}")

                # Chatworkメッセージを構築
                chatwork_message = f"""[info][title]LINE Webhookイベント受信[/title]
=== イベント情報 ===
イベントタイプ: {event_type}
イベントID: {event_id}
タイムスタンプ: {timestamp}
モード: {mode}
リプライトークン: {reply_token}

=== ソース情報 ===
ソースタイプ: {source_type}
ユーザーID: {user_id}
グループID: {group_id}
ルームID: {room_id}

=== メッセージ情報 ===
メッセージID: {message_id}
メッセージタイプ: {message_type}
引用メッセージID: {quoted_message_id}

=== 詳細情報 ===
{chr(10).join(detail_info) if detail_info else 'なし'}

=== 生データ (JSON) ===
{json.dumps(event, ensure_ascii=False, indent=2)}
[/info]"""

            else:
                # メッセージ以外のイベント（follow, unfollow, join, leave, etc.）
                chatwork_message = f"""[info][title]LINE Webhookイベント受信 ({event_type})[/title]
=== イベント情報 ===
イベントタイプ: {event_type}
イベントID: {event_id}
タイムスタンプ: {timestamp}
モード: {mode}
リプライトークン: {reply_token}

=== ソース情報 ===
ソースタイプ: {source_type}
ユーザーID: {user_id}
グループID: {group_id}
ルームID: {room_id}

=== 生データ (JSON) ===
{json.dumps(event, ensure_ascii=False, indent=2)}
[/info]"""

            # Chatworkに送信
            send_to_chatwork(chatwork_message)

        # 成功レスポンス
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')