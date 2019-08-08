from datetime import datetime
import json
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
from oandapyV20.endpoints.pricing import PricingStream
import pandas as pd
import pytz
import numpy as np

accountID = "101-001-10531929-001"
access_token = "70d74d6fe6d320399a4cc2c639d14561-eb0e01166e59d92331fedd308dd581f0"
api = API(access_token = access_token)



def order(units ,instrument,price):
    
    position_data = {
            "order":{
                "instrument": instrument,
                "units": units,
                # 1000通過単位で指定",
                # MARKET/成り行き注文   LIMIT/指値注文
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "stopLoss" : price
            }
        }
    ticket = orders.OrderCreate(accountID, data=position_data)
    api.request(ticket)
    
    

def long_position(instrument):
    # long  or  short
    data = {
        "longtUnits": "ALL"
    }
    # ドル円の買いポジションすべてを決済
    r = positions.PositionClose(accountID = accountID, data = data, instrument=instrument)
    api.request(r)


def short_position(instrument):
    # long  or  short
    data = {
        "shortUnits": "ALL"
    }
    # ドル円の買いポジションすべてを決済
    r = positions.PositionClose(accountID = accountID, data = data, instrument=instrument)
    api.request(r)


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


def bband(df,num):
    bband = pd.DataFrame()
    bband['close'] = df['close']
    mean = df['close'].mean()
    std = df['close'].std()
    upper = mean + (std * 2)
    lower= mean - (std * 2)


    return upper,lower



def TR(df):
    trs = []
    df['yopen'] = df.open.shift(+1)
    df['yhigh'] = df.high.shift(+1)
    df['ylow'] = df.low.shift(+1)
    df['yclose'] = df.close.shift(+1)

    i = 1
    while i < len(df):
        x = df['high'][i] - df['low'][i]
        y = df['high'][i] - df['yclose'][i]
        z = df['yclose'][i] - df['low'][i]

        if y <= x and x >= z:
            trs.append(x)
        elif x <= y and y >= z:
            trs.append(y) 
        elif x <= z and z >= y:
            trs.append(z) 

        i = i + 1

    return trs


def DMs(df):
    
    pDM = []
    mDM = []

    i = 1
    while i < len(df):
        moveUp = df['high'][i] - df['yhigh'][i]
        moveDown = df['ylow'][i] - df['low'][i]

        if 0 < moveUp and moveUp > moveDown:
            pDM.append(moveUp)
        else:
            pDM.append(0) 
        if 0 < moveDown and moveDown > moveUp:
            mDM.append(moveDown)
        else:
            mDM.append(0)
        i += 1

    # del df['yopen']
    # del df['yhigh']
    # del df['ylow']
    # del df['yclose']

    return pDM,mDM



def EMA(data,num):
    a = 2 / (num + 1)
    i = num 

    EMA_TR = []


    m = sum(data[:num]) / num
    EMA_TR.append(m)

    while i < len(data):
        m = m + (a * (data[i] - m))
        EMA_TR.append(m)

        i += 1



    # while i < len(df):
    #     df['EMA_TR'][i] = df['EMA_TR'][i-1] + (a * (df['TR'][i] - df['EMA_TR'][i-1]))
    #     df['EMA_+DM'][i] = df['EMA_+DM'][i-1] + (a * (df['+DM'][i] - df['EMA_+DM'][i-1]))
    #     df['EMA_-DM'][i] = df['EMA_-DM'][i-1] + (a * (df['-DM'][i] - df['EMA_-DM'][i-1]))
    #     i += 1


    return EMA_TR



def MACD(df,num):

    i = 0
    price = []
    while i < len(df):
        price.append(df['close'][i])
        i += 1

    return price

    # a = 2 / (num1 + 1)
    # i = num1 + 1
    # t = num2 + 1

    # df['EMA_S_close'] = df['close'].rolling(window=num1).mean()
    # df['EMA_L_close'] = df['close'].rolling(window=num2).mean()
    
    # while i < len(df):
    #     df['EMA_S_close'][i] = df['EMA_S_close'][i-1] + (a * (df['close'][i] - df['EMA_S_close'][i-1]))
    #     i += 1

    # while t < len(df):
    #     df['EMA_L_close'][t] = df['EMA_L_close'][t-1] + (a * (df['close'][t] - df['EMA_L_close'][t-1]))
    #     t += 1

    return df







    # tr = df['TR'].sum() 
    # print(tr) 

    # DIp = df['+DM'].sum() / tr * 100
    # DIm = df['-DM'].sum() / tr * 100
    


    # return DIp,DIm







# ボツ
# def smma(num,ashi,instrument,time,shift):
#     df = get_Mdata(num,ashi,instrument)
#     del df['open']
#     del df['close']
#     df['mid'] = (df['high'] + df['low']) / 2
#     # df['mid+2'] = df.mid.shift(+2)
#     column_name = 'smma'
#     column_name = "smma+1"
        
#     df.loc[time,column_name] = df.iloc[0:time,2].sum() / time
    
#     # df.il oc[plus(time),3] = (df.iloc[minus(time),3] * (minus(time)) + df.loc[plus(time),2]) / time
    
    
    
#     # df.loc[mask1,column_name] = 1
#     return df




