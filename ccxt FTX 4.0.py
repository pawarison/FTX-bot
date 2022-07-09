# ===============================================================================================================
# algo trading robot V.4.0
# Last modified: 2022-03-31 
# developed by Tan & Tao
# ===============================================================================================================
import ccxt
import configparser
from datetime import datetime
import numpy as np
import talib as ta
import pandas as pd
import time
import warnings
from loguru import logger
warnings.filterwarnings('ignore')

# ===============================================================================================================
# Global configuration
# ===============================================================================================================
config = configparser.ConfigParser() 
config.read('key.ini') # load key

robot_name = 'ActionZone'
robot_api_key = config['key']['apikey'] 
robot_secret_key = config['key']['secretkey']
robot_symbol = 'BTC-PERP' # trade symbol
robot_timeframe = '1m' # support timeframe: 1m, 3m, 5m, 15m, 1h
robot_max_candles = 100 # total candles to be loaded from exchange, max is 1,000
robot_riskpertrade = 0.0001 # 1%
robot_position_size_limit = 1 # max position size to allow to trade
robot_leverage = 20 # set leverage

exchange = ccxt.ftx({
    'apiKey' : robot_api_key ,
    'secret' : robot_secret_key ,
    'enableRateLimit': True,
    'option' : {'defaultType' : 'future', 'adjustForTimeDifference': True}
})
exchange.headers = {
    'FTX-SUBACCOUNT': 'testAPI',
}

log_history = 'log_history.csv'
log_ontrade = 'log_ontrade.csv'
log_status = 'log_status.log'

logger.add(log_status, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", retention= "30 days") # Cleanup after some time

response = exchange.private_post_account_leverage({'leverage': robot_leverage,}) 
print(exchange.fetchStatus())
logger.info(f'Status : {exchange.fetchStatus()}')

# ===============================================================================================================
# Utility Function
# ===============================================================================================================
def get_time():    
    now = datetime.now()
    formatted_date = now.strftime("%Y/%m/%d %H:%M:%S") 
    return formatted_date

def get_wallet():
    i=0 
    while i< 5:
        try:
            wallet = exchange.privateGetWalletBalances()['result']
            return wallet
        except Exception as e:
            if i >5:
                print(f'[{get_time()}]MAX RETRY {i} , {str(e)} Cannot GET {get_wallet.__name__}')
                logger.debug(f'Cant get get_wallet Function, MAX RETRY {i} !!')
                return  None
            else:
                print(str(e) , get_wallet.__name__, f' RETRY {i}')
                logger.debug(f'Cant get get_wallet Function, Retry round {i}')
                time.sleep(5)
                i+=1

def get_cash():
    try:
        wallet = get_wallet()
        for t in wallet:
            if t['coin'] in  ['USD']:
                cash = float(t['availableWithoutBorrow'])
        return cash
    except Exception as e:
        print(str(e))
        logger.debug('Cant get get_cash Function')
    
def get_position(symbols): 
    i= 0 
    while i <5 :
        try:
            res = exchange.fetchPositions()
            for sym in res:
                if sym['info']['future']==symbols:
                    f_pos = sym['info']
            return f_pos
        except Exception as e:
            if i >5:
                print(f'[{get_time()}]MAX RETRY {i} , {str(e)} Cannot GET {get_position.__name__}')
                logger.debug(f'Cant get get_position Function, MAX RETRY {i} !!')
                return  None
            else:
                print(str(e) , get_position.__name__, f' RETRY {i}')
                logger.debug(f'Cant get get_position Function, Retry round {i}')
                time.sleep(5)
                i+=1

def get_ticker(symbol):
    i= 0
    while i< 5:
        try:
            res =exchange.fetch_ticker(symbol)
            return res
        except Exception as e:
            if i >5:
                print(f'[{get_time()}]MAX RETRY {i} , {str(e)} Cannot GET {get_ticker.__name__}')
                logger.debug(f'Cant get get_ticker Function, MAX RETRY {i} !!')
                return  None
            else:
                print(str(e) , get_ticker.__name__, f' RETRY {i}')
                logger.debug(f'Cant get get_ticker Function, Retry round {i}')
                time.sleep(5)
                i+=1    

def get_price_digit(symbol): 
    try:
        res = get_ticker(symbol)
        price_step = float(res['info']['priceIncrement'])
        str_digit = str(price_step)
        count_digit = len(str_digit.split('.')[1])
        return count_digit
    except Exception as e :
        print(str(e))
        logger.debug('Cant get get_price_digit Function')
    
def get_size_digit(symbol): 
    try:
        res = get_ticker(symbol)
        size_step = float(res['info']['sizeIncrement'])
        last_price = float(res['info']['last'])
        min_provide = size_step * last_price
        str_digit = str(size_step)
        count_digit = len(str_digit.split('.')[1])
        return count_digit
        
    except Exception as e :
        print(str(e))
        logger.debug('Cant get get_size_digit Function')
 
def get_minimum_size(symbol): 
    res = get_ticker(symbol)['info']
    minimum_size = float(res['sizeIncrement'])
    last_bid = float(res['bid'])
    min_value = minimum_size * last_bid
    return float(minimum_size)

def check_positions():
    i= 0
    while i <5 :
        try:
            res = exchange.private_get_positions()['result']   
            for symbol in res:
                if symbol['future'] in robot_symbol:
                    netsize = float(symbol['netSize'])
                    if netsize > 0:
                        positions = 1 # Have Long Positions
                    elif netsize < 0:
                        positions = -1 # Have Short Positions
                    else :
                        positions = 0 # No Positions
                    return positions  
        except Exception as e:
            if i >5:
                print(f'[{get_time()}]MAX RETRY {i} , {str(e)} Cannot GET {check_positions.__name__}')
                logger.debug(f'Cant get check_positions Function, MAX RETRY {i} !!')
                return  None
            else:
                print(str(e) , check_positions.__name__, f' RETRY {i}')
                logger.debug(f'Cant get check_positions Function, Retry round {i}')
                time.sleep(5)
                i+=1 

def get_ohlcv(symbols = robot_symbol, timeframe = robot_timeframe, limit = robot_max_candles):
    i=0 
    while i < 5:
        try:
            bars = exchange.fetch_ohlcv(symbols, timeframe, limit = limit)
            return bars
        except Exception as e:
            if i >5:
                print(f'[{get_time()}]MAX RETRY {i} , {str(e)} Cannot GET {get_ohlcv.__name__}')
                logger.debug(f'Cant get get_ohlcv Function, MAX RETRY {i} !!')
                return  None
            else:
                print(str(e) , get_ohlcv.__name__, f' RETRY {i}')
                logger.debug(f'Cant get get_ohlcv Function, Retry round {i}')
                time.sleep(5)
                i+=1

def fetch_data(symbols = robot_symbol, timeframe = robot_timeframe, limit = robot_max_candles):
    try:        
        bars = get_ohlcv(symbols, timeframe, limit = limit)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except :
        print('LOAD DATA ERROR')
        logger.debug('LOAD DATA ERROR ')
        return pd.DataFrame()

def is_new_bar(prev_bar_time, cur_bar_time):
    if cur_bar_time > prev_bar_time:
        return True
    else:
        return False  

def get_my_trades(symbols = robot_symbol,since_ts=None):
    i= 0 
    res_trades = []
    while (i < 5) : # Try to Fetch until res != []
        try:
            if since_ts !=None:
                res_trades = exchange.fetch_my_trades(symbols, since=int(since_ts))
                while  res_trades == [] :
                    print(f'Try to get Trades {i}')
                    res_trades = exchange.fetch_my_trades(symbols, since=int(since_ts))
                    if i >= 20:
                        print('Over Try Limit to Fetch Trades')
                    i +=1
                    time.sleep(1)
            else:
                res_trades = exchange.fetch_my_trades(symbols)

            return res_trades
        except Exception as e:
            if i >5:
                print(f'[{get_time()}]MAX RETRY {i} , {str(e)} Cannot GET {get_my_trades.__name__}')
                logger.debug(f'Cant get get_my_trades Function, MAX RETRY {i} !!')
                return  None
            else:
                print(str(e) , get_my_trades.__name__, f' RETRY {i}')
                logger.debug(f'Cant get get_my_trades Function, Retry round {i}')
                time.sleep(5)
                i+=1

def load_last_ts_entry(last_side):
    ''' Fetch last Timestamp filter by side , symbols '''
    all_ts = []
    res_trades = get_my_trades(robot_symbol)
    for i in res_trades:
        if i['side'] == last_side:
            all_ts.append((i['timestamp']))
            last_ts =min(all_ts)
            return last_ts
        
robot_min_size = get_minimum_size(robot_symbol)

# ===============================================================================================================
# Order Function
# ===============================================================================================================
def create_open_market_order(symbols:str, side:str, size:float, params={}):  ### Custom param
        try:
            orderInfo = exchange.create_order(symbols, 'market',side , size, params = params)["info"]
            orderID = orderInfo["id"]
            entry_ts = exchange.parse8601(orderInfo['createdAt'])
            print(f'Time sleep To Fetch Trades {entry_ts}') 
            time.sleep(5)
            res_trades = get_my_trades(symbols, since_ts=int(entry_ts))
            if res_trades != []:
                entry_df_ts  = pd.DataFrame(res_trades)
                entry_df  = entry_df_ts.groupby('symbol').agg({'timestamp':'last','side':'last','price':'mean','amount':'sum','cost':'sum'}).reset_index()
                return entry_df
            else:
                print('Cannot Fetch last Trades')
                return pd.DataFrame()
        except Exception as e:
                print(f'[{get_time()}], {str(e)} Cannot GET {create_open_market_order.__name__}')
                logger.debug("Cannot GET create_open_market_order Function")
                return  None
    
def close_positions(symbols=robot_symbol):    
    close_df = pd.DataFrame()
    netsize = float(get_position(symbols)['netSize'])
    if netsize > 0:
        close_df = create_open_market_order(symbols, side='sell', size=abs(netsize), params={'conditionalOrdersOnly':True}) 
        if (not close_df.empty):
            close_df = close_df.add_suffix('_exit')     
    elif netsize < 0:  
        close_df = create_open_market_order(symbols, side='buy', size=abs(netsize), params={'conditionalOrdersOnly':True})
        close_df = close_df.add_suffix('_exit')
    else :
        print('No positions to close')
    return close_df

# ===============================================================================================================
# Ontrade log Function
# ===============================================================================================================
def read_log_ontrade():
    ''' Read Csv ontrade Files'''
    try:
        df =pd.read_csv(log_ontrade, usecols=['symbol','timestamp','side','price','amount','cost','stop_loss','take_profit'])
        print('Read Trade Files ')
        return df
    except :
        print('Create ontrade Files')
        logger.info('Create ontrade Files')
        df =pd.DataFrame(columns=['symbol','timestamp','side','price','amount','cost','stop_loss','take_profit'])
        return df
    
def reset_log_ontrade():
    ''' Reset DataFrame and save to ontrade Files'''
    df = pd.DataFrame(columns=['symbol','timestamp','side','price','amount','cost','stop_loss','take_profit'])
    df.to_csv(log_ontrade)
    return df

def load_log_ontrade(df,entry_df):
    ''' Load Position and calculation SL,tp if Not HoldPostion Reset Trades Files '''
    last_position = check_positions()
    print(last_position)
    if  (not entry_df.empty):
        if last_position == 1:
            f_pos = get_position(robot_symbol)
            entry_df.symbol =  [robot_symbol]
            entry_df['timestamp'] = [int(load_last_ts_entry(f_pos['side'])/1000)]
            entry_df['price'] =  [float(f_pos['recentAverageOpenPrice'])  ]
            entry_df['side'] = [f_pos['side']] 
            entry_df['amount'] =  [float(f_pos['size'])]
            entry_df['cost'] = [float(f_pos['size']) * float(f_pos['recentAverageOpenPrice'])]
            entry_df['stop_loss'] = [float(f_pos['recentAverageOpenPrice']) - Cal_SLdistance(df) ] 
            entry_df['take_profit'] = [0.0]
        elif last_position == -1:
            f_pos = get_position(robot_symbol)
            entry_df.symbol =  [robot_symbol]
            entry_df['timestamp'] = [int(load_last_ts_entry(f_pos['side'])/1000)]
            entry_df['price'] =  [float(f_pos['recentAverageOpenPrice'])  ]
            entry_df['side'] = [f_pos['side']] 
            entry_df['amount'] =  [float(f_pos['size'])]
            entry_df['cost'] = [float(f_pos['size']) * float(f_pos['recentAverageOpenPrice'])]
            entry_df['stop_loss'] = [float(f_pos['recentAverageOpenPrice']) + Cal_SLdistance(df)] 
            entry_df['take_profit'] = [0.0]

        else: # Postion == 0 if not have position reset_trade_log
            entry_df = reset_log_ontrade()
    else:
        if last_position == 1:
            latest_log = {}
            f_pos = get_position(robot_symbol)
            latest_log['symbol'] =  f_pos['future']
            latest_log['entry_time'] = df['timestamp'].iloc[-1]
            latest_log['entry_price'] =  float(f_pos['recentAverageOpenPrice'])  
            latest_log['position_side'] = f_pos['side'] 
            latest_log['position_amount'] =  float(f_pos['size'])
            latest_log['stop_loss'] = float(f_pos['recentAverageOpenPrice']) - Cal_SLdistance(df)  
            latest_log['take_profit'] = 0.0
            entry_df = pd.DataFrame([latest_log])

        elif last_position == -1:
            latest_log = {}
            f_pos = get_position(robot_symbol)
            latest_log['symbol'] =  f_pos['future']
            latest_log['entry_time'] = df['timestamp'].iloc[-1]
            latest_log['entry_price'] =  float(f_pos['recentAverageOpenPrice'])  
            latest_log['position_side'] = f_pos['side'] 
            latest_log['position_amount'] =  float(f_pos['size'])
            latest_log['stop_loss'] = float(f_pos['recentAverageOpenPrice']) + Cal_SLdistance(df)  
            latest_log['take_profit'] = 0.0
            entry_df = pd.DataFrame([latest_log])
        else: 
            entry_df = reset_log_ontrade()

    return entry_df

# ===============================================================================================================
# History log Function
# ===============================================================================================================
def close_trades(entry_df, exit_df):
    if not entry_df.empty:
        trades_df = pd.concat([entry_df,exit_df],axis=1)
        side_= trades_df['side'][0]
        if side_ =='buy':
            trades_df['diff_price'] = trades_df['price_exit'] - trades_df['price'] 
            trades_df['pnl'] = trades_df['cost_exit'] - trades_df['cost'] 
            trades_df =trades_df.reset_index()
        else:
            trades_df['diff_price'] =  trades_df['price'] -trades_df['price_exit']
            trades_df['pnl'] =  trades_df['cost'] - trades_df['cost_exit'] 
            trades_df =trades_df.reset_index()       
    else:
        trades_df =pd.DataFrame()
    return trades_df

def save_trades(all_trades, trades_df):
    ''' Save Trades Record to log_history'''
    if not trades_df.empty:
        all_trades = all_trades.append(trades_df).set_index('symbol')
        all_trades.to_csv(log_history)
        print('RECORD TRADES')
    else:
        print('Cannot Get Trades Details')
        pass
    
def read_log_history():
    ''' Read Csv log_history Files'''
    try:
        df= pd.read_csv(log_history)
        print('---DataBase Loaded---')

    except:
        df= pd.DataFrame(columns=['symbol','timestamp','side','price','amount','cost'])
        df.to_csv(log_history, index=False)
        print("---DataBase Created---")
        logger.info("---DataBase Created---")
    return df

# ===============================================================================================================
# Strategy Function Zone
# ===============================================================================================================
def Cal_Size(df, robot_riskpertrade = robot_riskpertrade):
    try:
        cash = get_cash()
        size= 0.0
        if cash != None:
            riskpertrade = robot_riskpertrade * cash
            size = (riskpertrade / Cal_SLdistance(df)) 
            if size > robot_position_size_limit:
                size = robot_position_size_limit
            elif size < robot_min_size:
                size = robot_min_size    
        return round(size, get_size_digit(robot_symbol))
    except Exception as e:
        print(str(e) , Cal_Size.__name__)
        logger.debug('Cant Cal_Size')

def Cal_SLdistance(df, vol_multiply = 1.2):
    vol = ta.STDDEV(df.close,30).ewm(alpha=0.96).mean()
    sl_distance = vol * vol_multiply
    return sl_distance.iloc[-1]

def Cal_TPdistance(df, vol_multiply = 1.5):
    vol = ta.STDDEV(df.close,30).ewm(alpha=0.96).mean()
    tp_distance = vol * vol_multiply
    return tp_distance.iloc[-1]

def strategy(df):    
    if (not df.empty) :
        df['ema1'] = ta.EMA(df.close, 12)
        df['ema2'] = ta.EMA(df.close, 26)
        
        df['LongEntries'] = (df['ema1'] > df['ema2']) & (df['ema1'].shift(1) < df['ema2']) & (df.close > df['ema1'])
        df['LongExit'] = df.close < df['ema2']   
        df['ShortEntries'] = (df['ema1'] < df['ema2']) & (df['ema1'].shift(1) > df['ema2']) & (df.close < df['ema1'])
        df['ShortExit'] = df.close > df['ema2'] 
        return df
    
    else:
        print('Cant Fetch Data' )
        logger.debug('Cant Fetch Data')
        return df            

# ===============================================================================================================
# Core Function
# ===============================================================================================================
def trading():
    global prev_bar
    global exit_df
    
    now_dt =get_time()
    
    if prev_bar != 0:
        prev_bar_str = datetime.utcfromtimestamp(int(prev_bar/1000))
    else:
        prev_bar_str= []
        
    df_raw = fetch_data()
    df = strategy(df_raw) # add fetchingdata to strategy

    print(f'RUN BOT  @ {now_dt} ')
    if  not df.empty:
        LongEntries = df['LongEntries'].iloc[-1] 
        LongExit = df['LongExit'].iloc[-1]   
        ShortEntries = df['ShortEntries'].iloc[-1]
        ShortExit = df['ShortExit'].iloc[-1]
        size = Cal_Size(df)
        
        print('Long : ',LongEntries,LongExit )    
        print('SHORT: ',ShortEntries,ShortExit )
        
        cur_bar_str =   df.timestamp.iloc[-1]
        cur_bar_time = int(cur_bar_str.timestamp()*1000) #
        new_bar_cond = is_new_bar(prev_bar,cur_bar_time)
        last_position = check_positions()
        last_price = df['close'].iloc[-1]
        
        entry_df = read_log_ontrade() 
        
        if not entry_df.empty  :
            print(f" Latest Position Holding : {entry_df}")     
            print('----------------------------------------')
        else:
            print(f" Position {robot_symbol} Position Side : {last_position}")
        
        if (prev_bar != cur_bar_time) :
            print('NEW BAR')
            if last_position == 0: 
                if LongEntries == True:    
                    entry_df = create_open_market_order(robot_symbol, 'buy', size = size)
                    entry_df = load_log_ontrade(df, entry_df) 
                    time.sleep(2)
                    entry_df.to_csv(log_ontrade)
                    
                    print("------ Open Long ------")

                elif ShortEntries == True: 
                    entry_df = create_open_market_order(robot_symbol,'sell',size=size)
                    entry_df = load_log_ontrade(df,entry_df) # WITH SL ,TP
                    entry_df.to_csv(log_ontrade)
                    time.sleep(2)

                    print("------ Open Short ------")

                else :
                    print('No Positions and Signals')
                    entry_df = reset_log_ontrade()

    
            elif last_position == 1:
                if LongExit == True :
                    exit_df = close_positions(robot_symbol)
                    trades_df = close_trades(entry_df,exit_df)
                    save_trades(read_log_history(),trades_df)
                    entry_df = load_log_ontrade(df,entry_df) # Close Reset
                    time.sleep(2)
                    entry_df.to_csv(log_ontrade)
                    print("------ Exit Long ------")

                elif  (not entry_df['symbol'].empty):
                    if (entry_df['take_profit'][0] != 0.0) and (last_price >= entry_df['take_profit'][0]):
                        exit_df = close_positions(robot_symbol)
                        trades_df = close_trades(entry_df,exit_df)
                        save_trades(read_log_history(),trades_df)
                        entry_df = load_log_ontrade(df,entry_df) # Close Reset
                        time.sleep(2)
                        entry_df.to_csv(log_ontrade)
                        print('TAKE PROFIT Long')
                        
                    elif entry_df['take_profit'][0] == 0.0:
                        print('Not Set TP')
                    
                elif (not entry_df['symbol'].empty) :
                    if (entry_df['stop_loss'][0] != 0.0) and (last_price <= entry_df['stop_loss'][0]) :
                        exit_df =close_positions(robot_symbol)
                        trades_df =close_trades(entry_df,exit_df)
                        save_trades(read_log_history(),trades_df)
                        entry_df = load_log_ontrade(df,entry_df) # Close Reset
                        time.sleep(2)
                        entry_df.to_csv(log_ontrade)
                        print('STOPLOSS Long')

                    elif entry_df['stop_loss'][0] == 0.0:
                        print('NOT SET SL')
                        
                elif ShortEntries == True: # Reverse Signal
                    exit_df = close_positions(robot_symbol)
                    trades_df = close_trades(entry_df,exit_df)
                    save_trades(read_log_history(), trades_df)
                    entry_df = load_log_ontrade(df, entry_df) # Close Reset
                    entry_df = create_open_market_order(robot_symbol, 'sell', size=size)
                    entry_df = load_log_ontrade(df,entry_df) # Calculation tp ,sl to entry_dataframe
                    time.sleep(2)
                    entry_df.to_csv(log_ontrade)
                    print("------ Open Short ------")
                    
                else:
                    print('Have Long Positions, No signal')
                    if entry_df['symbol'].empty or entry_df['price'].empty: # have position but lastest_log not calculation 
                        entry_df = load_log_ontrade(df,entry_df) # Close Reset
                        time.sleep(2)
                        entry_df.to_csv(log_ontrade)
                        print('NEW ', entry_df)
                    else:
                        print('Holding ', entry_df)
                                                
                        
            elif last_position== -1: # Have Short Positions 

                if ShortExit == True :
                    exit_df = close_positions(robot_symbol)
                    trades_df = close_trades(entry_df,exit_df)
                    save_trades(read_log_history(),trades_df)     
                    entry_df = load_log_ontrade(df,entry_df) # Close Reset
                    time.sleep(2)
                    entry_df.to_csv(log_ontrade)
                    print("------ Exit Short ------")

                elif (not entry_df['symbol'].empty):
                    if (entry_df['take_profit'][0] != 0.0) and (last_price <= entry_df['take_profit'][0]):

                        exit_df = close_positions(robot_symbol)
                        trades_df = close_trades(entry_df,exit_df)
                        save_trades(read_log_history(),trades_df)
                        entry_df = load_log_ontrade(df,entry_df) # Close Reset
                        time.sleep(2)
                        entry_df.to_csv(log_ontrade) 
                        print('TAKE PROFIT Short')

                    elif entry_df['take_profit'][0] == 0.0:
                        print('Not Set TP')
                        
                elif  (not entry_df['symbol'].empty) :
                    if (entry_df['stop_loss'][0] != 0.0) and (last_price >= entry_df['stop_loss'][0]):

                        exit_df = close_positions(robot_symbol)
                        trades_df = close_trades(entry_df,exit_df)
                        save_trades(read_log_history(),trades_df)
                        entry_df = load_log_ontrade(df,entry_df) # Close Reset
                        time.sleep(2)
                        entry_df.to_csv(log_ontrade)
                        print('STOPLOSS Short')   

                    elif entry_df['stop_loss'][0] == 0.0:
                        print('Not Set SL' )
                        
                elif LongEntries == True: # Reverse Signal
                    exit_df = close_positions(robot_symbol)
                    trades_df = close_trades(entry_df,exit_df)
                    save_trades(read_log_history(),trades_df)
                    entry_df = load_log_ontrade(df,entry_df) # Close Reset
                    entry_df = create_open_market_order(robot_symbol,'sell',size=size)
                    entry_df = load_log_ontrade(df,entry_df) 
                    time.sleep(2)
                    entry_df.to_csv(log_ontrade)
                    print("------ Open Long ------")

                else:
                    print('Have Short Positions, No signal')
                    if entry_df['symbol'].empty or  entry_df['price'].empty: # have position but lastest_log not calculation 
                        entry_df = load_log_ontrade(df,entry_df) # Close Reset
                        time.sleep(2)
                        entry_df.to_csv(log_ontrade)

                        print('NEW ',entry_df)
                    else:
                        print('Holding' ,entry_df)

        else:
            print('SAMEBAR')

        prev_bar = cur_bar_time
        print('-'*50)
        
    else:
        print('Can Not get DataFrame')
        logger.debug('Can Not get DataFrame')
        pass        
    
# ===============================================================================================================
# Run
# ===============================================================================================================
import vectorbt as vbt
prev_bar = 0
exit_df = pd.DataFrame()
logger.info(f'{robot_symbol} BOT, Time Frame {robot_timeframe}, RPT {robot_riskpertrade*100:.2f}, MAX LEVERAGE {robot_leverage}')
print(f'{robot_symbol} BOT, Time Frame {robot_timeframe}, RPT {robot_riskpertrade*100:.2f}, MAX LEVERAGE {robot_leverage}')
print('-'*50)
scheduler = vbt.ScheduleManager()
scheduler.every('minute', ':02').do(trading)
scheduler.start()        