from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
from oandapyV20.endpoints.pricing import PricingStream
import pandas as pd
import pytz
import numpy as np
from flask import Flask, request, abort
from flask.logging import create_logger
import os
from urllib import request as req
from bs4 import BeautifulSoup
import urllib.parse as parse

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)
log = create_logger(app)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

accountID = "101-001-10531929-001"
access_token = "70d74d6fe6d320399a4cc2c639d14561-eb0e01166e59d92331fedd308dd581f0"
api = API(access_token = access_token)

# 通貨の選択
instrument = "USD_JPY"

@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    log.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)



def handle_message(event):
    
    params = {
        "count": 1,
        "granularity": 'S5'  # 1時間足
    }

    # 過去データリクエスト
    res = instruments.InstrumentsCandles(instrument=instrument, params=params)
    api.request(res)
    data = []
    for raw in res.response['candles']:
        data.append([raw['time'], raw['volume'], raw['mid']['o'], raw['mid']['h'], raw['mid']['l'], raw['mid']['c']])

    df = pd.DataFrame(data)
    df.columns = ['time', 'volume', 'open', 'high', 'low', 'close']
    del df['time']
    del df['volume']

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=df['close']))



if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)







