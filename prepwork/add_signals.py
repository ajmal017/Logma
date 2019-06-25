import numpy as np
import pandas as pd
import sys, os
import seaborn as sns

from joblib import Parallel, delayed

from argparse import ArgumentParser

from consts import dir_

######################################################################################################
### This script generates the signals of a given instrument. Specify the windows that each of the
### signals will be calculated at. 
######################################################################################################

windows = [20, 30, 50]
cutoff = 100
std_cutoff = 3
n_jobs = 6
input_dir_ = 'D:/TickData_UZ_FW'

################################################

def long_short_ttc(datetime, df, opens, highs, lows, closes):
    
	idx = df[df.Datetime == datetime].index.values[0]
	target = opens[idx]
	avg_price = closes[idx]
	close, low = np.inf, np.inf
	drawdown = 0

	ctr = idx

	while close > target and low > target:

		try:

			idx += 1
			close = closes[idx]
			low = lows[idx]
			drawdown = min(drawdown, avg_price - highs[idx])

			if idx - ctr >= cutoff:
			    break

		except Exception as e:

			print(e)
			idx = ctr - 1

	return idx - ctr, drawdown

def short_long_ttc(datetime, df, opens, highs, lows, closes):
    
	idx = df[df.Datetime == datetime].index.values[0]
	target = opens[idx]
	avg_price = closes[idx]
	close, high = -np.inf, -np.inf
	drawdown = 0

	ctr = idx
	while close < target and high < target:

		try:

			idx += 1
			close = closes[idx]
			high = highs[idx]
			drawdown = min(drawdown, lows[idx] - avg_price)
			if idx - ctr >= cutoff:
				break

		except Exception as e:

			print(e)
			idx = ctr - 1
			break

	return idx - ctr, drawdown

def get_signals(ticker):

	print(ticker)

	df = pd.read_csv('D:/TickData_Agg_FW/{}.csv'.format(ticker))
	df['Change'] = (df.Close - df.Open) / df.Open

	for window in windows:

	    std_label = 'STD{}'.format(window)
	    mean_label = 'Mean{}'.format(window)

	    df[std_label] = df.Change.rolling(window=window, min_periods=1).std()
	    df[mean_label] = df.Change.rolling(window=window, min_periods=1).mean()

	## Compute Signals
	longs = df[(df.STD20 != 0) & (df.Volume != 0) & ((df.Change > df.Mean20 + df.STD20*std_cutoff) | (df.Change > df.Mean30 + df.STD30*std_cutoff) | (df.Change > df.Mean50 + df.STD50*std_cutoff))]
	shorts = df[(df.STD20 != 0) & (df.Volume != 0) & ((df.Change < df.Mean20 - df.STD20*std_cutoff) | (df.Change < df.Mean30 - df.STD30*std_cutoff) | (df.Change < df.Mean50 - df.STD50*std_cutoff))]

	## Make the features
	df['sig20'] = ((df.Change > df.Mean20 + df.STD20*std_cutoff) | (df.Change < df.Mean20 - df.STD20*std_cutoff)).astype(int)
	df['sig30'] = ((df.Change > df.Mean30 + df.STD30*std_cutoff) | (df.Change < df.Mean30 - df.STD30*std_cutoff)).astype(int)
	df['sig50'] = ((df.Change > df.Mean50 + df.STD50*std_cutoff) | (df.Change < df.Mean50 - df.STD50*std_cutoff)).astype(int)

	print('Num Longs', longs.shape[0])
	print('Num Shorts', shorts.shape[0])

	opens = df.Open.values
	highs = df.High.values
	lows = df.Low.values
	closes = df.Close.values

	ttc_long = []
	print('TTC Longs')

	for i, datetime in enumerate(longs.Datetime):
	    ttc, drawdown = long_short_ttc(datetime, df, opens, highs, lows, closes)
	    ttc_long.append([ttc, drawdown])

	ttc_longs = pd.DataFrame(ttc_long, columns=['TTC', 'Drawdown'])
	ttc_longs['Datetime'] = longs.Datetime.values
	ttc_longs['Direction'] = -1
	print(ttc_longs.describe())

	ttc_short = []
	print('TTC Shorts')
	for i, datetime in enumerate(shorts.Datetime):
	    ttc, drawdown = short_long_ttc(datetime, df, opens, highs, lows, closes)
	    ttc_short.append([ttc, drawdown])

	ttc_shorts = pd.DataFrame(ttc_short, columns=['TTC', 'Drawdown'])
	ttc_shorts['Datetime'] = shorts.Datetime.values
	ttc_shorts['Direction'] = 1
	print(ttc_shorts.describe())

	trades = pd.concat([ttc_longs, ttc_shorts], axis=0).sort_values('Datetime')
	trades = trades.merge(df[['Datetime', 'sig20', 'sig30', 'sig50', 'Volume']], on='Datetime', how='outer').dropna()
	trades = trades[trades.Volume != 0].iloc[:, :-1]

	trades.to_csv('{}/AddTrades_FW/{}_trades.csv'.format(dir_, ticker), index=False)

def get_tickers():

	tickers = []

	for file in os.listdir(input_dir_):
		ticker = file.split('-')[0]
		tickers.append(ticker) if ticker not in tickers else None

	return tickers

def go_parallel():

	Parallel(n_jobs=n_jobs)(delayed(get_signals)(ticker) for ticker in get_tickers())

def main(ticker):

	if ticker == 'ALL':
		go_parallel()
	else:
		get_signals(ticker)

if __name__ == '__main__':

	argparser = ArgumentParser()
	argparser.add_argument('ticker')
	args = argparser.parse_args()

	sys.exit(main(args.ticker))