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
import sys 
import csv 


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

accountID = ""
access_token = ""
api = API(access_token = access_token)

instrument = "GBP_USD"
ashi = "M5"
stoploss= 0.0020


position = 0
order_price = 0

yobi = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
nowweekday = datetime.now().strftime("%A")



def main(position,order_price):

    now_time = datetime.now().strftime("%H:%M:%S")
    
    # 現在の価格取得s
    now_price = moju.get_Mdata(1,ashi,instrument)['close'][0]
    print("現在レート:",now_price)
    

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
        moju.order(-2000,instrument,price)
        position = -1
        order_price = now_price
        print("short:",order_price)
        with open('trade.csv','a') as f:
            write = csv.writer(f)
            write.writerow([now_time,order_price,"short"])
        

    # # ロング、条件
    if now_price <= lower and pDI < mDI and MACD[-1] < signal[-1] and position == 0:
        price  = now_price - stoploss #損切りline
        moju.order(2000,instrument,price)
        position = 1
        order_price = now_price
        print("long:",order_price)
        with open('trade.csv','a') as f:
            write = csv.writer(f)
            write.writerow([now_time,order_price,"long"])


    # 決済
    if position == -1 and now_price < lower and MACD[-1] <= signal[-1]:
        moju.short_position(instrument)
        print("売り決済")
        position = 0
        order_price = 0
        price = abs(order_price - now_price)
        with open('trade.csv','a') as f:
            write = csv.writer(f)
            write.writerow([now_time,now_price,order_price,price,"売り決済"])

    if position == 1 and now_price > lower and MACD[-1] >= signal[-1]:
        moju.short_position(instrument)
        print("買い決済")
        position = 0
        order_price = 0
        price = now_price - order_price
        with open('trade.csv','a') as f:
            write = csv.writer(f)
            write.writerow([now_time,now_price,order_price,price,"決済"])

    # 損切り
    if position == -1 and now_price > order_price + stoploss:
        moju.short_position(instrument)
        position = 0
        order_price = 0
        price = order_price - now_price
        with open('trade.csv','a') as f:
            write = csv.writer(f)
            write.writerow([now_time,now_price,order_price,price,"売り損切り"])

    if position == 1 and now_price < order_price - stoploss:
        moju.long_position(instrument)
        position = 0
        order_price = 0
        price = now_price - order_price
        with open('trade.csv','a') as f:
            write = csv.writer(f)
            write.writerow([now_time,now_price,order_price,price,"買い損切り"])


    return position,order_price
    



if __name__ == "__main__":
#    app.run()
    yobi = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    position = 0
    count = 0
    for i in yobi:
        if i == datetime.now().strftime("%A"):
            now_weekday = count
        count = count + 1

    while(now_weekday != 6 | now_weekday != 7):
        position,order_price = main(position,order_price)
        time.sleep(60)
        count = 0
        for i in yobi:
            if i == datetime.now().strftime("%A"):
                now_weekday = count
            count = count + 1






