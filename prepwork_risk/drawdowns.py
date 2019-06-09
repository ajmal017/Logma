from joblib import Parallel, delayed
import pandas as pd
import numpy as np
import sys, os
import joblib

############################

## Tick Increments
tick_increments = {
    "EURCHF" : 0.00005,
    "USDCHF" : 0.00005,
    "GBPUSD" : 0.00005,
    "USDJPY" : 0.005,
    "EURUSD" : 0.00005,
    "EURGBP" : 0.00005,
    "NZDUSD" : 0.00005,
    "USDCAD" : 0.00005,
    "EURJPY" : 0.005,
    "AUDUSD" : 0.00005,
    "GBPJPY" : 0.005,
    "CHFJPY" : 0.005,
    "AUDNZD" : 0.00005,
    "CADJPY" : 0.005
}
tick_increments = {key : value / 5 for key, value in tick_increments.items()}
tick_value = 10

def get_candle_drawdowns(ticker):

	try:

		print('Ticker:', ticker)

		with open("../models/lgbm_2019-04-16", 'rb') as file:
			predictor = joblib.load(file)

		trades = pd.read_csv("D:/AlgoMLData/AddTrades/{}_trades.csv".format(ticker))
		raw = pd.read_csv("D:/TickData_Agg/{}.csv".format(ticker))
		scaled = pd.read_csv("D:/AlgoMLData/Scaled/{}_scaled.csv".format(ticker)).dropna()

		trades = trades[trades.Datetime.isin(scaled.Datetime.values)]
		scaled = scaled[scaled.Datetime.isin(trades.Datetime.values)]
		print(ticker, trades.shape, scaled.shape)
		trades['Pred'] = predictor.predict(scaled.iloc[:, 3:].values)
		trades = trades[trades.Pred == 1]

		raw.drop(['Volume', 'Ticks', 'VWAP'], axis=1, inplace=True)
		idc = raw[raw.Datetime.isin(trades.Datetime.values)].index.values
		idc = [np.arange(idx, idx+ttc+1).astype(int).tolist() for idx, ttc in zip(idc, trades.TTC.values)]
		dfs = [raw.iloc[idx, :] for i, idx in enumerate(idc)]
		[df.insert(1, 'Anchor', df.Open.values[0]) for df in dfs]
		[df.insert(1, 'CandleSize', abs(df.Open.values[0] - df.Close.values[0]) / tick_increments[ticker]) for df in dfs]
		[df.insert(1, 'Direction', dir_) for df, dir_ in zip(dfs, trades.Direction.values)]
		[df.insert(1, 'Trade_ID', i) for i, df in enumerate(dfs)]

		main = pd.concat(dfs)
		main = main.reset_index()
		main = main.set_index(main['index'].astype(str) + ' ' + main.Trade_ID.astype(str))
		idc_last = [str(idx[-1]) + ' ' + str(i) for i, idx in enumerate(idc)]

		tmp = main.loc[idc_last, :]
		long = tmp[tmp.Direction == 1]
		short = tmp[tmp.Direction == -1]
		long.loc[(long.Close > long.Anchor) | (long.High > long.Anchor), 'Close'] = long[(long.Close > long.Anchor) | (long.High > long.Anchor)].Anchor
		short.loc[(short.Close < short.Anchor) | (short.Low < short.Anchor), 'Close'] = short[(short.Close < short.Anchor) | (short.Low < short.Anchor)].Anchor
		main.loc[short.index, :] = short.values
		main.loc[long.index, :] = long.values

		main['RDD'] = abs(main.Close - main.Anchor)
		main['MDD'] = 1
		main.loc[main.Direction == -1, 'MDD'] = abs(main[main.Direction == -1].Anchor - main[main.Direction == -1].High)
		main.loc[main.Direction == 1, 'MDD'] = abs(main[main.Direction == 1].Anchor - main[main.Direction == 1].Low)
		main.loc[idc_last, 'MDD'] = [0 if min(x) == 0 else max(x) for x in main[main.index.isin(idc_last)][['RDD', 'MDD']].values]
		main['RDD'] = main.RDD / tick_increments[ticker]
		main['MDD'] = main.MDD / tick_increments[ticker]
		trade_progs = [main[main.Trade_ID == i] for i in range(main.Trade_ID.nunique())]

		drawdowns = {
		    i : [] for i in range(100)
		}
		for df in trade_progs:
		    for i, dd in enumerate(df.RDD[1:]):
		        drawdowns[i].append(dd)

		with open('D:/AlgoMLData/Progressions/{}_progs.pkl'.format(ticker), 'wb') as file:
			joblib.dump(trade_progs, file)

		with open('D:/AlgoMLData/Drawdowns/{}_dd.pkl'.format(ticker), 'wb') as file:
			joblib.dump(drawdowns, file)

	except Exception as e:

		print(ticker, e)

def go_parallel():

	Parallel(n_jobs = 6)(delayed(get_candle_drawdowns)(ticker) for ticker in tick_increments)

if __name__ == '__main__':

	go_parallel()

