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
import moju
import time
from datetime import datetime

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

def get_Mdata(num,ashi,instrument):

    params = {
        "count": num,
        "granularity": ashi  # 1時間足
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

    return df.astype(float)


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
    
    instrument = "GBP_USD"
    ashi = "M5"
    stoploss= 0.0020


    startminute = datetime.now().minute
    starthour = datetime.now().hour
    startday = datetime.now().day

    nowminute = datetime.now().minute
    nowhour = datetime.now().hour
    nowday = datetime.now().day

    position = 0

    line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ok")) 

    while((nowday - startday)*24*60+(nowhour - starthour)*60+(nowminute - startminute)<180):
    # 現在の価格取得
        now_price = get_Mdata(1,ashi,instrument)['close'][0]
        

        # ボリンジャーバンド2σ取得
        num_bb = 20 #期間
        upper,lower = moju.bband(moju.get_Mdata(num_bb,ashi,instrument),num_bb)
        

        # dmi
        # 期間14
        num_dmi = 14
        df_dmi = moju.get_Mdata(num_dmi*2,ashi,instrument)
        trs = moju.TR(df_dmi)
        pDM,mDM = moju.DMs(df_dmi)
        EMA_TR = moju.EMA(trs,num_dmi)
        EMA_pDM = moju.EMA(pDM,num_dmi)
        EMA_mDM = moju.EMA(mDM,num_dmi)

        pDI = EMA_pDM[-1] / EMA_TR[-1] * 100
        mDI = EMA_mDM[-1] / EMA_TR[-1] * 100
        
        

        # ema_tr = moju.EMA(trs,num_dmi)

        # del df_dmi['TR']
        # del df_dmi['+DM']
        # del df_dmi['-DM']

        # df_dmi['+DI'] = 100 * (df_dmi['EMA_+DM'] / df_dmi['EMA_TR'])
        # df_dmi['-DI'] = 100 * (df_dmi['EMA_-DM'] / df_dmi['EMA_TR'])


        # # MACD
        # #12,26,9
        num1_macd = 12
        num2_macd = 26
        num3_macd = 9

        df_macd = moju.get_Mdata(num2_macd*2,ashi,instrument)
        macd_s = moju.MACD(df_macd,num1_macd)
        macd_l = moju.MACD(df_macd,num2_macd)
        EMA_s = moju.EMA(macd_s,num1_macd)
        EMA_l = moju.EMA(macd_l,num2_macd)
        del EMA_s[:14]
        

        i = 0
        MACD = []
        while i < len(EMA_l):
            MACD.append(EMA_s[i] - EMA_l[i])
            i += 1

        signal = moju.EMA(MACD,num3_macd)

        


        # 損切り20pips
        # ショート、条件
        # 2σにタッチ
        # positive lineが20以上  なし   
        # +DMが-DMより上
        # MACDがsignal lineより上
        # if now_price > bband['upper']:
        # position = 0
        if now_price >= upper and pDI > mDI and MACD[-1] > signal[-1] and position == 0:
            price = now_price + stoploss #損切りline
            moju.order(-10000,instrument,price)
            position = -1
            # order_price = now_price
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="short"))  
            

        # # ロング、条件
        if now_price <= lower and pDI < mDI and MACD[-1] < signal[-1] and position == 0 :
            price  = now_price - stoploss #損切りline
            moju.order(10000,instrument,price)
            position = 1
            # order_price = now_price
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="long"))  


        # 決済
        if position == -1 and now_price < lower and MACD[-1] <= signal[-1]:
            moju.short_position(instrument)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="売り決済")) 
            position = 0

        if position == 1 and now_price > lower and MACD[-1] >= signal[-1]:
            moju.short_position(instrument)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="買い決済")) 
            position = 0


        time.sleep(60*2)

        nowminute = datetime.now().minute
        nowhour = datetime.now().hour
        nowday = datetime.now().day






if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)







