import os
import sys

from flask import Flask, request, abort

from linebot.v3 import WebhookHandler

from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

from openai import AzureOpenAI

# get LINE credentials from environment variables
channel_access_token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
channel_secret = os.environ["LINE_CHANNEL_SECRET"]

if channel_access_token is None or channel_secret is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)

# get Azure OpenAI credentials from environment variables
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_model = os.getenv("AZURE_OPENAI_MODEL")

if azure_openai_endpoint is None or azure_openai_api_key is None or azure_openai_api_version is None:
    raise Exception(
        "Please set the environment variables AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_API_VERSION."
    )


handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)


ai = AzureOpenAI(
    azure_endpoint=azure_openai_endpoint, api_key=azure_openai_api_key, api_version=azure_openai_api_version
)


# LINEボットからのリクエストを受け取るエンドポイント
@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        abort(400, e)

    return "OK"


chat_history = []


# 　AIへのメッセージを初期化する関数
def init_chat_history():
    chat_history.clear()
    system_role = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "あなたはユーモアがあり、周りの人たちから好かれている人です。友達と話すような感じ。",
            },
        ],
    }
    chat_history.append(system_role)


# 　返信メッセージをAIから取得する関数
def get_ai_response(from_user, text):
    # ユーザのメッセージを記録
    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": text,
            },
        ],
    }
    chat_history.append(user_msg)

    # AIのパラメータ
    parameters = {
        "model": azure_openai_model,  # AIモデル
        "max_tokens": 1000,  # 返信メッセージの最大トークン数
        "temperature": 0.5,  # 生成の多様性（0: 最も確実な回答、1: 最も多様な回答）
        "frequency_penalty": 0,  # 同じ単語を繰り返す頻度（0: 小さい）
        "presence_penalty": 0,  # すでに生成した単語を再度生成する頻度（0: 小さい）
        "stop": ["\n"],
        "stream": False,
    }

    # AIから返信を取得
    ai_response = ai.chat.completions.create(messages=chat_history, **parameters)
    res_text = ai_response.choices[0].message.content

    # AIの返信を記録
    ai_msg = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": res_text},
        ],
    }
    chat_history.append(ai_msg)
    return res_text


# 　返信メッセージを生成する関数
def generate_response(from_user, text):
    res = []
    if text in ["リセット", "初期化", "クリア", "reset", "clear"]:
        # チャット履歴を初期化
        init_chat_history()
        res = [TextMessage(text="チャットをリセットしました。")]
    else:
        # AIを使って返信を生成
        res = [TextMessage(text=get_ai_response(from_user, text))]
    return res


# メッセージを受け取った時の処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    # 送られてきたメッセージを取得
    text = event.message.text

    # 返信メッセージの送信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        res = []
        if isinstance(event.source, UserSource):
            # ユーザー情報が取得できた場合
            profile = line_bot_api.get_profile(event.source.user_id)
            # 返信メッセージを生成
            res = generate_response(profile.display_name, text)
        else:
            # ユーザー情報が取得できなかった場合
            # fmt: off
            # 定型文の返信メッセージ
            res = [
                TextMessage(text="ユーザー情報を取得できませんでした。"),
                TextMessage(text=f"メッセージ：{text}")
            ]
            # fmt: on

        # メッセージを送信
        line_bot_api.reply_message_with_http_info(ReplyMessageRequest(reply_token=event.reply_token, messages=res))

import json
import os
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

# LINE Botの認証情報を環境変数から取得
channel_access_token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
channel_secret = os.environ["LINE_CHANNEL_SECRET"]

if channel_access_token is None or channel_secret is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

app = Flask(__name__)

# ポケモン図鑑データ（特徴を追加）
pokedex = [
    {
        "name": "ナエトル",
        "type": ["くさ"],
        "color": "みどり",
        "evolution": True,
        "habitat": "森",
        "classification": "わかばポケモン",
        "weight": "軽い",
        "height": "小さい",
    },
    {
        "name": "ドダイトス",
        "type": ["くさ", "じめん"],
        "color": "みどり",
        "evolution": False,
        "habitat": "森",
        "classification": "だいちポケモン",
        "weight": "重い",
        "height": "大きい",
    },
    {
        "name": "ポッチャマ",
        "type": ["みず"],
        "color": "あお",
        "evolution": True,
        "habitat": "海",
        "classification": "ペンギンポケモン",
        "weight": "軽い",
        "height": "小さい",
    },
    {
        "name": "エンペルト",
        "type": ["みず", "はがね"],
        "color": "あお",
        "evolution": False,
        "habitat": "海",
        "classification": "かいていポケモン",
        "weight": "重い",
        "height": "大きい",
    },
    # 必要に応じて追加
]

# 初期化用の変数
current_candidates = pokedex.copy()
current_question_index = 0
questions = [
    {"key": "type", "question": "そのポケモンはどのタイプですか？", "options": ["くさ", "ほのお", "みず", "じめん", "はがね"]},
    {"key": "color", "question": "そのポケモンの色は何ですか？", "options": ["みどり", "あか", "あお"]},
    {"key": "habitat", "question": "そのポケモンはどこに住んでいますか？", "options": ["森", "山", "海"]},
    {"key": "classification", "question": "そのポケモンの分類は何ですか？", "options": ["わかばポケモン", "だいちポケモン", "ペンギンポケモン", "かいていポケモン"]},
    {"key": "weight", "question": "そのポケモンの体重はどのくらいですか？", "options": ["軽い", "普通", "重い"]},
    {"key": "height", "question": "そのポケモンの高さはどのくらいですか？", "options": ["小さい", "普通", "大きい"]},
    {"key": "evolution", "question": "そのポケモンは進化しますか？", "options": ["はい", "いいえ"]},
]

# ゲームの初期化
def reset_game():
    global current_candidates, current_question_index
    current_candidates = pokedex.copy()
    current_question_index = 0


# 質問を取得
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
# 候補を絞り込む（修正済み）
def filter_candidates(key, value):
    global current_candidates
    if key == "evolution":
        value = value == "はい"  # "はい"をTrue、"いいえ"をFalseとして解釈
    current_candidates = [
        p for p in current_candidates if value in (p[key] if isinstance(p[key], list) else [p[key]])
    ]


# ユーザーの回答を処理（修正済み）
def process_user_response(user_response):
    global current_question_index

    # リセット処理
    if user_response in ["リセット", "reset"]:
        reset_game()
        return "ゲームをリセットしました！"

    # 現在の質問に応じた回答処理
    if current_question_index < len(questions):
        q = questions[current_question_index]

        # 正しい選択肢を確認
        if user_response not in q["options"]:
            return f"正しい選択肢を入力してください: {', '.join(q['options'])}"

        # フィルタリング
        filter_candidates(q["key"], user_response)
        current_question_index += 1  # 次の質問へ進む
        return ask_question()

    # 候補が1つに絞られた場合
    if len(current_candidates) == 1:
        return f"答えは {current_candidates[0]['name']} です！"

    # 候補がなくなった場合
    if not current_candidates:
        return "該当するポケモンが見つかりませんでした。リセットしてください。"

    return "質問が終了しましたが、特定できませんでした。リセットしてください。"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)