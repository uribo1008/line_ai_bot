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
pokemon_data = [
    {
        "name": "ナエトル",
        "type": ["くさ"],
        "abilities": ["しんりょく"],
        "classification": "はっぱポケモン",
        "height": 0.4,  # メートル
        "weight": 10.2,  # キログラム
        "number": 387,
        "evolution": {
            "previous": None,
            "next": ["ハヤシガメ"]
        },
        "description": "ひなたで　からだを　あたためる。　こうらの　うえの　はっぱで　ひがしるし　が　わかる。",
    },
    {
        "name": "ハヤシガメ",
        "type": ["くさ"],
        "abilities": ["しんりょく"],
        "classification": "うみがめポケモン",
        "height": 1.1,
        "weight": 97.0,
        "number": 388,
        "evolution": {
            "previous": ["ナエトル"],
            "next": ["ドダイトス"]
        },
        "description": "つちの　なかから　えいようを　すいとると　せなかの　くさが　そだつ。　のやまに　すむ。",
    },
    {
        "name": "ドダイトス",
        "type": ["くさ", "じめん"],
        "abilities": ["しんりょく"],
        "classification": "たいりくポケモン",
        "height": 2.2,
        "weight": 310.0,
        "number": 389,
        "evolution": {
            "previous": ["ハヤシガメ"],
            "next": None
        },
        "description": "せなかの　おおきな　きの　まわりに　ちいさな　ポケモンが　あつまって　くらす。",
    },
    {
        "name": "ヒコザル",
        "type": ["ほのお"],
        "abilities": ["もうか"],
        "classification": "こざるポケモン",
        "height": 0.5,
        "weight": 6.2,
        "number": 390,
        "evolution": {
            "previous": None,
            "next": ["モウカザル"]
        },
        "description": "おしりから　でている　ひは　きぶんで　もえかたが　かわる。　あめの　ひは　ちいさくなる。",
    },
    {
        "name": "ポッチャマ",
        "type": ["みず"],
        "abilities": ["げきりゅう"],
        "classification": "ペンギンポケモン",
        "height": 0.4,
        "weight": 5.2,
        "number": 393,
        "evolution": {
            "previous": None,
            "next": ["ポッタイシ"]
        },
        "description": "みずを　はっしゃして　きょうてきに　ちょうせんする。　プライドが　たかく　なかなか　なつかない。",
    },
    # チェリンボ
    {
        "name": "チェリンボ",
        "type": ["くさ"],
        "abilities": ["しんりょく"],
        "classification": "さくらんぼポケモン",
        "height": 0.6,
        "weight": 3.3,
        "number": 412,
        "evolution": {
            "previous": None,
            "next": ["チェリム"]
        },
        "description": "きの　うえで　ちいさな　さくらんぼの　ような　はっぱを　さかせる。　かわいい　みたけ。",
    },
    # チェリム
    {
        "name": "チェリム",
        "type": ["くさ"],
        "abilities": ["しんりょく"],
        "classification": "さくらんぼポケモン",
        "height": 0.6,
        "weight": 3.3,
        "number": 413,
        "evolution": {
            "previous": ["チェリンボ"],
            "next": None
        },
        "description": "すごく　あたたかい　ひざしの　なかで　こうふんした　おおきな　さくらの　ように　なります。",
    },
    # ズバット
    {
        "name": "ズバット",
        "type": ["どく", "ひこう"],
        "abilities": ["においぶくろ"],
        "classification": "コウモリポケモン",
        "height": 0.8,
        "weight": 7.5,
        "number": 41,
        "evolution": {
            "previous": None,
            "next": ["ゴルバット"]
        },
        "description": "よるに　うごきだす。　あしが　きかないので　ひこうことに　よろこびを　みせる。",
    },
    # ゴルバット
    {
        "name": "ゴルバット",
        "type": ["どく", "ひこう"],
        "abilities": ["においぶくろ"],
        "classification": "コウモリポケモン",
        "height": 1.6,
        "weight": 55.0,
        "number": 42,
        "evolution": {
            "previous": ["ズバット"],
            "next": None
        },
        "description": "ひこうしんこうを　しんけんに　しようとする。　そのため　しょっきん　さつじんこうの　ように　においぶくろを　ふくらませる。",
    },
    # コリンク
    {
        "name": "コリンク",
        "type": ["でんき"],
        "abilities": ["いかく"],
        "classification": "いぬポケモン",
        "height": 0.5,
        "weight": 9.5,
        "number": 404,
        "evolution": {
            "previous": None,
            "next": ["ルクシオ"]
        },
        "description": "あたまの　ひかりで　けんこうを　かんさつして　おしりから　しっぽを　うごかして　けいこうを　よそおう。",
    },
    # ルクシオ
    {
        "name": "ルクシオ",
        "type": ["でんき"],
        "abilities": ["いかく"],
        "classification": "いぬポケモン",
        "height": 0.9,
        "weight": 30.5,
        "number": 405,
        "evolution": {
            "previous": ["コリンク"],
            "next": ["ライボルト"]
        },
        "description": "しっぽの　うごきを　ひかりの　しるしとし　うしろ　かみと　しごとを　しながら　おおよそ　ちょうせんする。",
    },
    # ライボルト
    {
        "name": "ライボルト",
        "type": ["でんき"],
        "abilities": ["いかく"],
        "classification": "でんきポケモン",
        "height": 1.5,
        "weight": 30.5,
        "number": 406,
        "evolution": {
            "previous": ["ルクシオ"],
            "next": None
        },
        "description": "でんきの　いろの　ひを　なげることで　こうか　がある。　かんきょうの　ひこうの　いま。",
    },

    # タテトプス
    {
        "name": "タテトプス",
        "type": ["いわ", "はがね"],
        "abilities": ["がんじょう"],
        "classification": "かたくてポケモン",
        "height": 0.6,
        "weight": 26.0,
        "number": 410,
        "evolution": {
            "previous": None,
            "next": ["トリデプス"]
        },
        "description": "たての　ような　こうぼうは　かたく　なかなか　やぶれない。　あらしにも　くずれない。",
    },
    # トリデプス
    {
        "name": "トリデプス",
        "type": ["いわ", "はがね"],
        "abilities": ["がんじょう"],
        "classification": "かたくてポケモン",
        "height": 1.3,
        "weight": 150.0,
        "number": 411,
        "evolution": {
            "previous": ["タテトプス"],
            "next": None
        },
        "description": "あたまの　こうぼうで　ちょうせんし　いろんな　こうが　なかに　つめこまれた。",
    },
    # ミミロル
    {
        "name": "ミミロル",
        "type": ["ノーマル"],
        "abilities": ["うるおいボディ"],
        "classification": "うさぎポケモン",
        "height": 0.4,
        "weight": 5.5,
        "number": 427,
        "evolution": {
            "previous": None,
            "next": ["ミミロップ"]
        },
        "description": "うすあおい　ぴんくの　おおきな　みみを　もつ。おおきな　あたまは　だいぶ　たるみが　ある。",
    },
    # ミミロップ
    {
        "name": "ミミロップ",
        "type": ["ノーマル"],
        "abilities": ["うるおいボディ"],
        "classification": "うさぎポケモン",
        "height": 1.2,
        "weight": 28.3,
        "number": 428,
        "evolution": {
            "previous": ["ミミロル"],
            "next": None
        },
        "description": "めの　うるおいが　いいので　よく　じっとして　よく　みんなと　はじめた。",
    },
    # フカマル
    {
        "name": "フカマル",
        "type": ["ドラゴン", "じめん"],
        "abilities": ["すなかき"],
        "classification": "わだいポケモン",
        "height": 0.6,
        "weight": 20.5,
        "number": 443,
        "evolution": {
            "previous": None,
            "next": ["ガバイト"]
        },
        "description": "たちあがり　うごくたびに　しっかり　と　とらえるので　やる気を　見せる。",
    },
    # ガバイト
    {
        "name": "ガバイト",
        "type": ["ドラゴン", "じめん"],
        "abilities": ["すなかき"],
        "classification": "かいりゅうポケモン",
        "height": 1.0,
        "weight": 20.5,
        "number": 444,
        "evolution": {
            "previous": ["フカマル"],
            "next": ["ガブリアス"]
        },
        "description": "しっかり　うけつけるけど　すぐ　また　あきらめたために　せいちょうした。いろも　きめた。",
    },
    # ガブリアス
    {
        "name": "ガブリアス",
        "type": ["ドラゴン", "じめん"],
        "abilities": ["すなかき"],
        "classification": "けいひょうポケモン",
        "height": 1.8,
        "weight": 95.0,
        "number": 445,
        "evolution": {
            "previous": ["ガバイト"],
            "next": None
        },
        "description": "ひろがった　あたま　きもち　ちょっとおおきい。",
    },
    # マネネ
    {
        "name": "マネネ",
        "type": ["えん", "あお"],
        "abilities": ["あまもり"],
        "classification": "いたしうす",
        "height": 0.5,
        "weight": 9.2,
        "number": 435,
        "evolution": {
            "previous": None,
            "next": ["ピチュー"]
        },
        "description": "むこうに　おにんきな　おしっくにするけど　はなれても　とっても　じょうず。",
    },
    # ゴンベ
    {
        "name": "ゴンベ",
        "type": ["ノーマル"],
        "abilities": ["りこえる"],
        "classification": "ぽっちゃりポケモン",
        "height": 0.6,
        "weight": 30.5,
        "number": 425,
        "evolution": {
            "previous": None,
            "next": ["カビゴン"]
        },
        "description": "むきましときおなかが　ふくろだのを　はじめました。",
    },
    # ザングース
    {
        "name": "ザングース",
        "type": ["あお"],
        "abilities": ["ちょすう"],
        "classification": "かみつきポケモン",
        "height": 0.9,
        "weight": 26.3,
        "number": 327,
        "evolution": {
            "previous": None,
            "next": None
        },
        "description": "むきうまいきょうに　きけんすけの　ほらに　てかえた。",
    },
    # ヤドン
    {
        "name": "ヤドン",
        "type": ["みず"],
        "abilities": ["どくよけ"],
        "classification": "のんきポケモン",
        "height": 1.2,
        "weight": 36.0,
        "number": 79,
        "evolution": {
            "previous": None,
            "next": ["ヤドラン"]
        },
        "description": "とても　やさしい　たちあがりに　はらいにきた。",
    },
    # ヤドラン
    {
        "name": "ヤドラン",
        "type": ["みず", "どく"],
        "abilities": ["どくよけ"],
        "classification": "ねっこポケモン",
        "height": 1.5,
        "weight": 79.5,
        "number": 80,
        "evolution": {
            "previous": ["ヤドン"],
            "next": None
        },
        "description": "しずかにおとなしく　とくにかたよらない。",
    },
    # ツボツボ
    {
        "name": "ツボツボ",
        "type": ["むし", "いわ"],
        "abilities": ["きんちょうかん"],
        "classification": "にらみツボ",
        "height": 0.4,
        "weight": 5.0,
        "number": 213,
        "evolution": {
            "previous": None,
            "next": None
        },
        "description": "やることがない　ころに　かたわらであそんで　にらみをたくさんえた。",
    },
    # ドラピオン
    {
        "name": "ドラピオン",
        "type": ["あく", "むし"],
        "abilities": ["いわきし"],
        "classification": "さおのポケモン",
        "height": 1.3,
        "weight": 61.0,
        "number": 452,
        "evolution": {
            "previous": ["ツボツボ"],
            "next": None
        },
        "description": "ふくろがあったけど　すくあげした。",
    },
    # サマヨール
    {
        "name": "サマヨール",
        "type": ["ゴースト"],
        "abilities": ["ちょうはつ"],
        "classification": "おばけポケモン",
        "height": 1.0,
        "weight": 28.0,
        "number": 354,
        "evolution": {
            "previous": None,
            "next": ["サーナイト"]
        },
        "description": "かすかに動きながら　しばらく　とけたと。",
    },
    # ガラガラ
    {
        "name": "ガラガラ",
        "type": ["じめん"],
        "abilities": ["ほのおのひ"],
        "classification": "むしぶしポケモン",
        "height": 1.1,
        "weight": 42.0,
        "number": 105,
        "evolution": {
            "previous": None,
            "next": ["タネボー"]
        },
        "description": "にょる気。",
    },
    # ロコン
    {
        "name": "ロコン",
        "type": ["ほのお"],
        "abilities": ["もらいび", "ひでり"],
        "classification": "きつねポケモン",
        "height": 0.6,
        "weight": 9.9,
        "number": 37,
        "evolution": {
            "previous": None,
            "next": ["キュウコン"]
        },
        "description": "うまれたときから　しっぽが　いっぽん。しっぽの　ふえる　せいちょうとともに　わかれていく。",
    },
    # キュウコン
    {
        "name": "キュウコン",
        "type": ["ほのお"],
        "abilities": ["もらいび", "ひでり"],
        "classification": "きつねポケモン",
        "height": 1.1,
        "weight": 19.9,
        "number": 38,
        "evolution": {
            "previous": ["ロコン"],
            "next": None
        },
        "description": "ちょうじゅの　ポケモン。きゅうほんの　しっぽを　さわると　のろいを　うけるといわれている。",
    },
    # ユキカブリ
    {
        "name": "ユキカブリ",
        "type": ["くさ", "こおり"],
        "abilities": ["ゆきふらし", "ぼうおん"],
        "classification": "こゆきポケモン",
        "height": 1.0,
        "weight": 50.5,
        "number": 459,
        "evolution": {
            "previous": None,
            "next": ["ユキノオー"]
        },
        "description": "ゆきがふる　ちほうに　すむ。ゆきのなかに　とけこんで　えものを　まつ。",
    },
    # ユキノオー
    {
        "name": "ユキノオー",
        "type": ["くさ", "こおり"],
        "abilities": ["ゆきふらし", "ぼうおん"],
        "classification": "せいおうポケモン",
        "height": 2.2,
        "weight": 135.5,
        "number": 460,
        "evolution": {
            "previous": ["ユキカブリ"],
            "next": None
        },
        "description": "にんげんが　ちかづくと　ゆきあらしを　ふきおこして　おいはらおうとする。",
    },
    # ニャルマー
    {
        "name": "ニャルマー",
        "type": ["ノーマル"],
        "abilities": ["じゅうなん", "するどいめ"],
        "classification": "しつけポケモン",
        "height": 0.5,
        "weight": 3.9,
        "number": 431,
        "evolution": {
            "previous": None,
            "next": ["ブニャット"]
        },
        "description": "しっぽを　ふりながら　かわいく　なく。その　すがたに　だまされてしまう　トレーナーも　おおい。",
    },
    # ブニャット
    {
        "name": "ブニャット",
        "type": ["ノーマル"],
        "abilities": ["あついしぼう", "じゅうなん"],
        "classification": "いかくポケモン",
        "height": 1.0,
        "weight": 43.8,
        "number": 432,
        "evolution": {
            "previous": ["ニャルマー"],
            "next": None
        },
        "description": "ひとたび　おこると　しっぽを　ふくらませ　とても　こわい　かおになる。",
    },
    # ムウマ
    {
        "name": "ムウマ",
        "type": ["ゴースト"],
        "abilities": ["ふゆう"],
        "classification": "よなきポケモン",
        "height": 0.7,
        "weight": 1.0,
        "number": 200,
        "evolution": {
            "previous": None,
            "next": ["ムウマージ"]
        },
        "description": "なきごえで　ひとを　おどろかせるのが　だいすき。ほしの　ひかりを　たべて　いきている。",
    },
    # ムウマージ
    {
        "name": "ムウマージ",
        "type": ["ゴースト"],
        "abilities": ["ふゆう"],
        "classification": "まじょポケモン",
        "height": 0.9,
        "weight": 4.4,
        "number": 429,
        "evolution": {
            "previous": ["ムウマ"],
            "next": None
        },
        "description": "こえに　まほうが　こもる。わるだくみが　おおい　こわい　まじょポケモン。",
    },
    # チリーン
    {
        "name": "チリーン",
        "type": ["エスパー"],
        "abilities": ["ふゆう"],
        "classification": "かざぐるまポケモン",
        "height": 0.6,
        "weight": 1.0,
        "number": 358,
        "evolution": {
            "previous": ["リーシャン"],
            "next": None
        },
        "description": "ないた　おとを　たくさん　あつめたら　ちいさな　あめが　ふるという。",
    },
    # トゲピー
    {
        "name": "トゲピー",
        "type": ["フェアリー"],
        "abilities": ["はりきり", "てんのめぐみ"],
        "classification": "とげとげポケモン",
        "height": 0.3,
        "weight": 1.5,
        "number": 175,
        "evolution": {
            "previous": None,
            "next": ["トゲチック"]
        },
        "description": "まわりに　しあわせを　ふりまく　ポケモン。かこまれると　ほんわか　あたたかくなる。",
    },
    # トゲチック
    {
        "name": "トゲチック",
        "type": ["フェアリー", "ひこう"],
        "abilities": ["はりきり", "てんのめぐみ"],
        "classification": "しあわせポケモン",
        "height": 0.6,
        "weight": 3.2,
        "number": 176,
        "evolution": {
            "previous": ["トゲピー"],
            "next": ["トゲキッス"]
        },
        "description": "ひとの　よろこびを　さっちして　うれしそうに　とびまわる　ポケモン。",
    }
]

    # 必要に応じて追加


# 初期化用の変数
current_candidates = pokemon_data.copy()
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
    current_candidates = pokemon_data.copy()
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



# LINE Botからのリクエストを受け取る
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# LINEでメッセージを受け取ったときの処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    reply = process_user_response(user_message)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)],
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)