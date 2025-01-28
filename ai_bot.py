import os
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

# 必要な環境変数を取得
channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.environ.get("LINE_CHANNEL_SECRET")

if not channel_access_token or not channel_secret:
    print("環境変数 LINE_CHANNEL_ACCESS_TOKEN と LINE_CHANNEL_SECRET を設定してください。")
    sys.exit(1)

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)
app = Flask(__name__)

# ポケモン図鑑データ
pokedex = [
    {"name": "ナエトル", "type": ["くさ"], "color": "みどり", "evolution": True, "habitat": "森",
     "classification": "わかばポケモン", "weight": "軽い", "height": "小さい"},
    {"name": "ドダイトス", "type": ["くさ", "じめん"], "color": "みどり", "evolution": False, "habitat": "森",
     "classification": "だいちポケモン", "weight": "重い", "height": "大きい"},
    {"name": "ポッチャマ", "type": ["みず"], "color": "あお", "evolution": True, "habitat": "海",
     "classification": "ペンギンポケモン", "weight": "軽い", "height": "小さい"},
    {"name": "エンペルト", "type": ["みず", "はがね"], "color": "あお", "evolution": False, "habitat": "海",
     "classification": "かいていポケモン", "weight": "重い", "height": "大きい"},
]

questions = [
    {"key": "type", "question": "そのポケモンはどのタイプですか？", "options": ["くさ", "ほのお", "みず", "じめん", "はがね"]},
    {"key": "color", "question": "そのポケモンの色は何ですか？", "options": ["みどり", "あか", "あお"]},
    {"key": "habitat", "question": "そのポケモンはどこに住んでいますか？", "options": ["森", "山", "海"]},
    {"key": "classification", "question": "そのポケモンの分類は何ですか？", "options": ["わかばポケモン", "だいちポケモン", "ペンギンポケモン", "かいていポケモン"]},
    {"key": "weight", "question": "そのポケモンの体重はどのくらいですか？", "options": ["軽い", "普通", "重い"]},
    {"key": "height", "question": "そのポケモンの高さはどのくらいですか？", "options": ["小さい", "普通", "大きい"]},
    {"key": "evolution", "question": "そのポケモンは進化しますか？", "options": ["はい", "いいえ"]},
]

current_candidates = pokedex.copy()
current_question_index = 0


# ゲームのリセット
def reset_game():
    global current_candidates, current_question_index
    current_candidates = pokedex.copy()
    current_question_index = 0


# 質問を生成
def ask_question():
    global current_question_index

    if len(current_candidates) == 1:
        return f"答えは {current_candidates[0]['name']} です！"

    if not current_candidates:
        return "該当するポケモンが見つかりませんでした。ゲームをリセットしてください。"

    if current_question_index < len(questions):
        q = questions[current_question_index]
        return q["question"] + "\n" + " / ".join(q["options"])

    return "質問が終了しましたが、特定できませんでした。リセットしてください。"


# 候補を絞り込む
def filter_candidates(key, value):
    global current_candidates
    if key == "evolution":
        value = value == "はい"  # "はい"をTrue、"いいえ"をFalseとして解釈
    current_candidates = [
        p for p in current_candidates if value in (p[key] if isinstance(p[key], list) else [p[key]])
    ]


# ユーザーの応答を処理
def process_user_response(user_response):
    global current_question_index

    if user_response in ["リセット", "reset"]:
        reset_game()
        return "ゲームをリセットしました！"

    if current_question_index < len(questions):
        q = questions[current_question_index]
        if user_response not in q["options"]:
            return f"正しい選択肢を入力してください: {', '.join(q['options'])}"

        filter_candidates(q["key"], user_response)
        current_question_index += 1
        return ask_question()

    if len(current_candidates) == 1:
        return f"答えは {current_candidates[0]['name']} です！"

    if not current_candidates:
        return "該当するポケモンが見つかりませんでした。リセットしてください。"

    return "質問が終了しましたが、特定できませんでした。リセットしてください。"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_message = event.message.text
    reply_text = process_user_response(user_message)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
