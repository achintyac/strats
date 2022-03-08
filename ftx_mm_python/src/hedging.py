# import libs
import time
import hmac
from requests import Request, Session, Response
import requests
import urllib.parse
from typing import Optional, Dict, Any, List
from ciso8601 import parse_datetime
import pandas as pd
import datetime
import os
import asyncio
from dotenv import load_dotenv
from importlib import reload

# import clients
from client import FtxClient
from websocket_client import FtxWebsocketClient

# fees (Tier 1)
MAKER_FEES = 0.0002
TAKER_FEES = 0.0007

# get .env params
load_dotenv()
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')

# init clients
ftx_client = FtxClient(
    api_key=API_KEY,
    api_secret=SECRET_KEY
)

ftx_websocket_client = FtxWebsocketClient(
    api_key=API_KEY,
    api_secret=SECRET_KEY
)

dict_hedging_market = {"SOL-PERP": "SOL/USD"}

MARKET = "SOL-PERP"
MARKET_HEDGING = dict_hedging_market.get(MARKET)
COIN_HEDGED = MARKET_HEDGING.split("/")[0]
PLACE_TRADES = True
MIN_HEDGE_ORDER_SIZE_ALLOWED = 0.01
SLEEP_SECONDS = 3
# MAX_ORDERS = 6
# PNL_KILL_SWITCH = -20

def calc_net_position_open_orders(orders):
  temp_sum = 0
  for order in orders:
    if order['status'] == 'open' and order['side'] == 'buy':
      temp_sum += order['remainingSize']
    elif order['status'] == 'open' and order['side'] == 'sell':
      temp_sum -= order['remainingSize']
  return temp_sum

while True:
    current_positions = ftx_client.get_position(MARKET)
    # current_positions_hedged = ftx_client.get_position(MARKET_HEDGING)
    wallet_balances = ftx_client.get_balances()
    open_orders_hedge = ftx_client.get_open_orders(MARKET_HEDGING)
    hedge_coin_order_book = ftx_client.get_orderbook(MARKET_HEDGING)
    hedge_coin_index = next((index for (index, d) in enumerate(wallet_balances) if d["coin"] == COIN_HEDGED), None)

    execution_price_hedge = current_positions['recentBreakEvenPrice']
    perp_net_position = current_positions['netSize']
    hedge_coin_net_position = wallet_balances[hedge_coin_index]['total']
    pending_orders_net_size_hedge = calc_net_position_open_orders(open_orders_hedge)
    diff_pos_size = perp_net_position + hedge_coin_net_position + pending_orders_net_size_hedge

    # if not execution_price_hedge:
    top_of_book_bid_px = hedge_coin_order_book['bids'][0][0]
    top_of_book_ask_px = hedge_coin_order_book['asks'][0][0]
    ask_side_limit_px = top_of_book_ask_px
    bid_side_limit_px = top_of_book_bid_px

    if abs(diff_pos_size) < MIN_HEDGE_ORDER_SIZE_ALLOWED:
        pass
    elif diff_pos_size < 0 and PLACE_TRADES:

        print('buy hedge size {} at market price'.format(abs(diff_pos_size)))

        ftx_client.place_order(market=MARKET_HEDGING,
                               side="buy",
                               price=None,
                               size=abs(diff_pos_size),
                               type="market",
                               reduce_only=False,
                               ioc=False,
                               post_only=False,
                               )

    elif diff_pos_size > 0 and PLACE_TRADES:
        print('sell hedge size {} at market price '.format(abs(diff_pos_size)))

        ftx_client.place_order(market=MARKET_HEDGING,
                               side="sell",
                               price=None,
                               size=diff_pos_size,
                               type="market",
                               reduce_only=False,
                               ioc=False,
                               post_only=False,
                               )

    time.sleep(SLEEP_SECONDS)
