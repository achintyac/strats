from dotenv import load_dotenv
from client import FtxClient
import pandas as pd
import numpy as np
import os
import datetime
import requests

load_dotenv()
FILE_PATH_HIST = os.getenv('FILE_PATH_HIST')

ftx_client = FtxClient()

# removes Z from ISO string which indicates times are in UTC
def convert_date_format(df):
    df_hist_tweets.DATE = np.array(df_hist_tweets.DATE.str[:-1].values, dtype="datetime64")
    return df_hist_tweets

# tweet times from csv are in UTC
df_hist_tweets = pd.read_csv(FILE_PATH_HIST, engine="python", names=["TWEET", "TWEET_ID", "USER", "DATE", "RULE"])
df_hist_tweets = convert_date_format(df_hist_tweets)
print(df_hist_tweets)

# get historical spot
security = "SOL"
index_hist = ftx_client._get(path=f"/markets/{security}/USD/candles?resolution=15")
# df_index_hist = pd.DataFrame(index_hist)
# df_index_hist.drop(columns=['time', 'open','volume'], inplace=True)
# print(FtxClient.get_historical_prices("BTC/USD"))
print(index_hist)
