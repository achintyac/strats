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

dict_size = {"SOL-PERP": 1}
dict_edge = {"SOL-PERP": 10}

MARKET = "SOL-PERP"
DEPTH = 10
SIZE = dict_size.get(MARKET) # in native units (ie: 1 => 1 sol)
EDGE_BPS = dict_edge.get(MARKET)
EDGE_PCT = EDGE_BPS / (10000 * 2)
PLACE_TRADES = True
MAX_ORDERS = 4 # keep as multiple of 2
PNL_KILL_SWITCH = -10
SLEEP_SECONDS = 0.5

def is_cancelled_order(order):
    return (order['status'] == 'closed') and (order['filledSize'] == 0)

def calc_net_position_incl_open_orders(positions):
    realized_book_net_position = positions['netSize']
    open_orders_net_position = positions['longOrderSize'] - positions['shortOrderSize']
    return realized_book_net_position, open_orders_net_position

# {'future': 'SOL-PERP', 'size': 0.44, 'side': 'sell', 'netSize': -0.44, 'longOrderSize': 0.94, 'shortOrderSize': 0.5, 'cost': -38.9048, 'entryPrice': 88.42, 'unrealizedPnl': 0.0, 'realizedPnl': -1154.43162786, 'initialMarginRequirement': 0.33333333, 'maintenanceMarginRequirement': 0.03, 'openSize': 0.94, 'collateralUsed': 27.704933056284, 'estimatedLiquidationPrice': 2129.4708264318183, 'recentAverageOpenPrice': 88.2975, 'recentPnl': -0.0539, 'recentBreakEvenPrice': 88.2975, 'cumulativeBuySize': 0.0, 'cumulativeSellSize': 0.44}



while True:
    order_book = ftx_client.get_orderbook(MARKET, DEPTH)
    open_orders = ftx_client.get_open_orders(MARKET)
    current_positions = ftx_client.get_position(MARKET)
    order_history = ftx_client.get_order_history(MARKET)

    # print(current_positions)

    # kill switch
    if current_positions['recentPnl'] and current_positions['recentPnl'] < PNL_KILL_SWITCH and PLACE_TRADES:
        if current_positions['side'] == 'buy':
            ftx_client.place_order(market=MARKET,
                                   side="sell",
                                   price=None,
                                   size=current_positions['size'],
                                   type="market",
                                   reduce_only=True,
                                   ioc=False,
                                   post_only=False,
                                   )
            ftx_client.cancel_orders(MARKET)
            break

        else:
            ftx_client.place_order(market=MARKET,
                                   side="buy",
                                   price=None,
                                   size=current_positions['size'],
                                   type="market",
                                   reduce_only=True,
                                   ioc=False,
                                   post_only=False,
                                   )
            ftx_client.cancel_orders(MARKET)
            break

    # # on a big market spike the REST API can lag so we check to make sure positions
    # # and open orders balance and place balancing trades if needed
    # realized_net_position, open_orders_net_position = calc_net_position_incl_open_orders(current_positions)
    # if realized_net_position + open_orders_net_position == 0:
    #     pass
    # else:
    #     if realized_net_position < open_orders_net_position:
    #         diff_size = open_orders_net_position - realized_net_position
    #
    #         ftx_client.place_order(market=MARKET,
    #                                side="sell",
    #                                price=current_positions['recentBreakEvenPrice']*(1+EDGE_PCT),
    #                                size=diff_size,
    #                                type="limit",
    #                                reduce_only=False,
    #                                ioc=False,
    #                                post_only=True,
    #                                )
    #
    #     else:
    #         diff_size = realized_net_position - open_orders_net_position
    #
    #         ftx_client.place_order(market=MARKET,
    #                                side="buy",
    #                                price=current_positions['recentBreakEvenPrice']*(1-EDGE_PCT),
    #                                size=diff_size,
    #                                type="limit",
    #                                reduce_only=False,
    #                                ioc=False,
    #                                post_only=True,
    #                                )

    # post new orders if we get filled on one side
    if ((MAX_ORDERS * SIZE) >= current_positions['size']) and ((MAX_ORDERS-2) >= len(open_orders)) and PLACE_TRADES:
        top_of_book_bid_px = order_book['bids'][0][0]
        top_of_book_ask_px = order_book['asks'][0][0]
        ask_side_limit_px = top_of_book_ask_px
        bid_side_limit_px = top_of_book_bid_px

        ftx_client.place_order(market=MARKET,
                               side="sell",
                               price=ask_side_limit_px*(1+EDGE_PCT),
                               size=SIZE,
                               type="limit",
                               reduce_only=False,
                               ioc=False,
                               post_only=True,
                               )

        ftx_client.place_order(market=MARKET,
                               side="buy",
                               price=bid_side_limit_px*(1-EDGE_PCT),
                               size=SIZE,
                               type="limit",
                               reduce_only=False,
                               ioc=False,
                               post_only=True,
                               )

        print('requoting buy/sell orders because we got filled on side')
        print('buy at {} and sell at {}'.format(bid_side_limit_px*(1-EDGE_PCT), ask_side_limit_px*(1+EDGE_PCT)))

        # time.sleep(0.1)
        # open_orders = ftx_client.get_open_orders(MARKET)
        # current_positions = ftx_client.get_position(MARKET)
        order_history = ftx_client.get_order_history(MARKET)

        # print(current_positions)
        # print(order_history)

        # when 1 order gets cancelled on postOnly, prevents posting when market moving
        prev_order_1 = order_history[0]
        prev_order_2 = order_history[1]

        print("prev orders are:")
        print(prev_order_1)
        print(prev_order_2)

        # if is_cancelled_order(prev_order_1) and is_cancelled_order(prev_order_2):
        #     pass
        if is_cancelled_order(prev_order_1) and not is_cancelled_order(prev_order_2):
            print('cancelled previous order 2')
            try:
                ftx_client.cancel_order(prev_order_2['id'])
            except Exception:
                pass
        elif is_cancelled_order(prev_order_2) and not is_cancelled_order(prev_order_1):
            print('cancelled previous order 1')
            try:
                ftx_client.cancel_order(prev_order_1['id'])
            except Exception:
                pass

        time.sleep(SLEEP_SECONDS)
        continue
