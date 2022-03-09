from dotenv import load_dotenv
from client import FtxClient
import pandas as pd
import numpy as np
import os
import datetime
import requests

load_dotenv()
FILE_PATH_HIST = os.getenv('FILE_PATH_HIST')
FILE_PATH_PRICE_HIST = os.getenv('FILE_PATH_PRICE_HIST')
MAX_TIME_COVER_FOR_15_RESOLUTION = 22470000.0 # FTX timestamps in milliseconds
MIN_RESOLUTION = 15
RESOLUTION = 60
TIME_DIFF_BETWEEN_RESPONSES = RESOLUTION * 1000
TIME_DIFF_BETWEEN_START_AND_END = MAX_TIME_COVER_FOR_15_RESOLUTION * (RESOLUTION / MIN_RESOLUTION) # time differential between start and end times based on user determined resolution
TIME_ADJ_IN_HOURS = 8
RECORD_HISTORY = False
READ_HISTORY = True

ftx_client = FtxClient()

# removes Z from ISO string which indicates times are in UTC
def convert_date_format(df):
    df.DATE = np.array(df.DATE.str[:-1].values, dtype="datetime64")
    return df

def calc_time_params_for_pagination(ftx_api_response):
    start_time_of_request = ftx_api_response[0]["time"]
    start_time_for_next_request = start_time_of_request - TIME_DIFF_BETWEEN_RESPONSES - TIME_DIFF_BETWEEN_START_AND_END
    end_time_for_next_request = start_time_of_request - TIME_DIFF_BETWEEN_RESPONSES
    return start_time_of_request, start_time_for_next_request, end_time_for_next_request

# FTX API converts api inputs from ms to s
def convert_time_for_pagination(time_stamp):
    return int(time_stamp / 1000)

securities_lst = ["SOL", "BTC", "ETH", "LUNA", "AVAX", "FTM", "ADA", "DOT"]
df_hist_prices = pd.DataFrame()

if RECORD_HISTORY:
    for security in securities_lst:
        i = 0
        while i < 120:
            if i == 0:
                index_hist = ftx_client.get_historical_prices(security, RESOLUTION)
            else:
                index_hist = ftx_client.get_historical_prices(security,
                                                              RESOLUTION,
                                                              convert_time_for_pagination(start_time_for_next_request),
                                                              convert_time_for_pagination(end_time_for_next_request))

            start_time_of_request, start_time_for_next_request, end_time_for_next_request = calc_time_params_for_pagination(index_hist)

            df_prices = pd.DataFrame(index_hist)
            df_prices["currency"] = security
            df_prices.startTime = np.array(df_prices.startTime.values, dtype="datetime64") - np.timedelta64(TIME_ADJ_IN_HOURS, 'h')
            df_hist_prices = pd.concat([df_hist_prices, df_prices])
            # print("start time for current request: ", int(start_time_of_request/1000))
            # print("start time for next request: ", int(start_time_for_next_request/1000))
            # print("end time for next request: ", int(end_time_for_next_request/1000))
            # print(df_hist_prices)
            i += 1

    try:
        df_hist_prices = df_hist_prices.drop(columns=["volume"]) \
                                        .sort_values(by=["startTime"]) \
                                        .reset_index(drop=True)
        df_hist_prices.to_csv(FILE_PATH_PRICE_HIST, index=False)
        print("csv save succesful to: ", FILE_PATH_PRICE_HIST)
    except Exception as e:
        print("The following error happened in df cleaning/writing: ", e)


if READ_HISTORY:
    try:
        df_price_history = pd.read_csv(FILE_PATH_PRICE_HIST)

        # tweet times from csv are in UTC
        df_tweet_history = pd.read_csv(FILE_PATH_HIST, engine="python", names=["TWEET", "TWEET_ID", "USER", "DATE", "RULE"])
        df_tweet_history = convert_date_format(df_tweet_history)

        print(df_price_history)
        print(df_tweet_history)

    except Exception as e:
        print("Encountered following error when reading csv: ", e)
