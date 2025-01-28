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

app = Flask(__name__)
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
                "text": "あなたはコテコテの関西弁のおっちゃんです。周りからの信頼があつく、質問や会話の合間にあらゆるアドバイスや誉め言葉を発してくれます。口調は少しきついですが、文章の中にダジャレを組み込む高等なテクニックも持っています。",
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
from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

# LINE API credentials
channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.environ.get("LINE_CHANNEL_SECRET")

if not channel_access_token or not channel_secret:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET as environment variables.")
    sys.exit(1)

# Flask app and LINE webhook handler
app = Flask(__name__)
handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

# Expanded Pokémon data (Diamond & Pearl Pokédex)
pokemon_data = [
{"name": "ナエトル", "type": ["くさ"], "height": 0.4, "weight": 10.2, "ability": ["しんりょく"]},
    {"name": "ヒコザル", "type": ["ほのお"], "height": 0.5, "weight": 6.2, "ability": ["もうか"]},
    {"name": "ポッチャマ", "type": ["みず"], "height": 0.4, "weight": 5.2, "ability": ["げきりゅう"]},
    {"name": "ムクバード", "type": ["ノーマル", "ひこう"], "height": 0.6, "weight": 15.5, "ability": ["いかく", "するどいめ"]},
    {"name": "ビーダル", "type": ["ノーマル", "みず"], "height": 1.0, "weight": 31.5, "ability": ["たんじゅん", "てんねん"]},
    {"name": "コロトック", "type": ["むし"], "height": 1.0, "weight": 25.5, "ability": ["むしのしらせ"]},
    {"name": "ロズレイド", "type": ["くさ", "どく"], "height": 0.9, "weight": 14.5, "ability": ["しんりょく"]},
    {"name": "ガブリアス", "type": ["ドラゴン", "じめん"], "height": 1.9, "weight": 95.0, "ability": ["すながくれ"]},
    {"name": "ピカチュウ", "type": ["でんき"], "height": 0.4, "weight": 6.0, "ability": ["せいでんき"]},
    {"name": "ロコン", "type": ["ほのお"], "height": 0.6, "weight": 9.9, "ability": ["もらいび"]},
    {"name": "サンド", "type": ["じめん"], "height": 0.6, "weight": 12.0, "ability": ["すながくれ"]},
    {"name": "ズバット", "type": ["どく", "ひこう"], "height": 0.8, "weight": 7.5, "ability": ["せいしんりょく"]},
    {"name": "ゴルバット", "type": ["どく", "ひこう"], "height": 1.6, "weight": 55.0, "ability": ["せいしんりょく"]},
    {"name": "ニャース", "type": ["ノーマル"], "height": 0.4, "weight": 4.2, "ability": ["ものひろい"]},
    {"name": "イーブイ", "type": ["ノーマル"], "height": 0.3, "weight": 6.5, "ability": ["にげあし", "てきおうりょく"]},
    {"name": "エーフィ", "type": ["エスパー"], "height": 0.9, "weight": 26.5, "ability": ["シンクロ"]},
    {"name": "ブラッキー", "type": ["あく"], "height": 1.0, "weight": 27.0, "ability": ["シンクロ"]},
    {"name": "ラルトス", "type": ["エスパー", "フェアリー"], "height": 0.4, "weight": 6.6, "ability": ["シンクロ", "トレース"]},
    {"name": "キルリア", "type": ["エスパー", "フェアリー"], "height": 0.8, "weight": 20.2, "ability": ["シンクロ", "トレース"]},
    {"name": "サーナイト", "type": ["エスパー", "フェアリー"], "height": 1.6, "weight": 48.4, "ability": ["シンクロ", "トレース"]},
    {"name": "ハスボー", "type": ["みず", "くさ"], "height": 0.5, "weight": 2.6, "ability": ["すいすい", "あめうけざら"]},
    {"name": "ルンパッパ", "type": ["みず", "くさ"], "height": 1.5, "weight": 55.0, "ability": ["すいすい", "あめうけざら"]},
    {"name": "ドジョッチ", "type": ["みず", "じめん"], "height": 0.4, "weight": 1.9, "ability": ["どんかん", "すいすい"]},
    {"name": "ナマズン", "type": ["みず", "じめん"], "height": 0.9, "weight": 23.6, "ability": ["どんかん", "すいすい"]},
]

# Global variables for filtering process
pokemon_candidates = pokemon_data
filter_stage = "type"  # Current stage of filtering: "type", "ability", or "done"

# Function to filter Pokémon based on user responses
def filter_pokemon(pokemon_list, key, value):
    return [pokemon for pokemon in pokemon_list if value in pokemon.get(key, [])]

# Handle user messages
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    global pokemon_candidates, filter_stage
    user_message = event.message.text.strip()

    if user_message.lower() == "start":
        # Reset the game
        pokemon_candidates = pokemon_data
        filter_stage = "type"
        reply_text = "ポケモンアキネーターを始めます！まずポケモンのタイプを教えてください。例: くさ, ほのお, みず"
    elif filter_stage == "type":
        # Filter by type
        pokemon_candidates = filter_pokemon(pokemon_candidates, "type", user_message)
        if len(pokemon_candidates) == 0:
            reply_text = "該当するポケモンが見つかりませんでした。もう一度タイプを教えてください。例: くさ, ほのお, みず"
        elif len(pokemon_candidates) == 1:
            reply_text = f"あなたが思い浮かべているポケモンは {pokemon_candidates[0]['name']} です！"
            filter_stage = "done"
        else:
            filter_stage = "ability"
            reply_text = "次にポケモンの特性を教えてください。例: しんりょく, もうか, げきりゅう"
    elif filter_stage == "ability":
        # Filter by ability
        pokemon_candidates = filter_pokemon(pokemon_candidates, "ability", user_message)
        if len(pokemon_candidates) == 0:
            reply_text = "該当するポケモンが見つかりませんでした。もう一度特性を教えてください。例: しんりょく, もうか, げきりゅう"
        elif len(pokemon_candidates) == 1:
            reply_text = f"あなたが思い浮かべているポケモンは {pokemon_candidates[0]['name']} です！"
            filter_stage = "done"
        else:
            filter_stage = "done"
            reply_text = f"候補が複数あります: {[p['name'] for p in pokemon_candidates]}\n他の条件でも絞り込みたい場合は 'start' と入力してください。"
    else:
        reply_text = "すみません、現在の質問には対応していません。もう一度 'start' と入力してゲームを始めてください。"

    # Send reply
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(ReplyMessageRequest(
            reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]
        ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)