from joblib import Parallel, delayed
from argparse import ArgumentParser
import pandas as pd
import numpy as np
import sys, os
import time

from entropy import spectral_entropy, app_entropy
from statsmodels.tsa.stattools import adfuller
from scipy.stats import kurtosis

import warnings
warnings.filterwarnings("ignore")

from consts import *

######################################################################################################
### This script takes OHLC data as input and outputs timeseries features of a given instrument.
######################################################################################################

###################################
### GLOBAL VARIABLES
###################################

#Rel Vol 1-week MA
n_periods = 7
n_candles = 480

#Long/Short windows
short_window = 20
long_window = 50

n_jobs = 8

###################################
### GLOBAL FUNCTIONS
###################################

def filter_weekends(df):
	df['Datetime'] = pd.to_datetime(df.Datetime)
	df = df[~df.Datetime.dt.weekday_name.isin(['Saturday', 'Sunday'])]
	return df

def compute_relative_volume(df, n_periods, n_candles):
	
	#Align the dataset to start at a day
	idx = df.Datetime.astype(str).str.split(' ', expand=True)[1].values.tolist().index('00:00:00')
	df = df.iloc[idx:, :]
	
	cut_off = [i for i in range(0, len(df), n_candles)][-1]
	df = df.iloc[:cut_off, :]
	cumvol = np.array(np.split(df.Volume.values, int(len(df)/n_candles)))
	
	cumvol = np.cumsum(cumvol, axis=1)
	cumvol = cumvol.reshape(-1, )
	
	offset = n_periods * n_candles
	cumvol_final = [0 for i in range(offset)]
	
	for i in range(offset, len(df), n_candles):
		
		voldist = cumvol[i-offset:i]
		idc = np.arange(0, offset, n_candles)
		voldist = [voldist[idc+i].mean() for i in range(0, n_candles)]
		cumvol_final += voldist
	
	df['RelVol'] = np.divide(cumvol, cumvol_final)
	return df.iloc[offset:, :]

def approx_entropy(x):
	
	try:
		return app_entropy(x, order=2, metric='chebyshev')
	except:
		return np.nan
	
def spec_entropy(x):

	try:
		offset = x.shape[0]
		return spectral_entropy(x, sf=offset, method='welch', nperseg=(offset/8), normalize=True)
	except:
		return np.nan
	
def autocorrelation(x):
	
	try:
		return x.autocorr(11)
	except:
		return np.nan
	
def stationarity(x):
	
	try:
		t, _, _, _, t_crit, _ = adfuller(x, autolag = 'AIC')
		t_crit = list(t_crit.values())[1]
		return 0 if (t < t_crit or np.isnan(t)) else 1
	except Exception as e:
		return np.nan

def market_sessions(df):
	
	us = [[i, 1 - (i - 12) / 9] for i in range(12, 20)]
	eur = [[i, 1 - (i - 7) / 9] for i in range(7, 16)]
	asia = [[i, 1-(i+1) / 9] for i in range(0, 9)]
	asia = [[23, 1]] + asia

	#Market Hours
	df['Hour'] = pd.to_datetime(df.Datetime).dt.hour.astype(int)

	#Merge
	df = df.merge(pd.DataFrame(asia, columns=['Hour', 'Asia']), how='outer', on='Hour')
	df = df.merge(pd.DataFrame(us, columns=['Hour', 'Amer']), how='outer', on='Hour')
	df = df.merge(pd.DataFrame(eur, columns=['Hour', 'Eur']), how='outer', on='Hour')

	return df.drop('Hour', axis=1).fillna(0).sort_values('Datetime').reset_index(drop=True)

def features(ticker):

	warnings.filterwarnings("ignore")

	print(ticker)

	def cp(x):
		return x.cumprod()[-1]

	df = pd.read_csv(data_dir/ticker)
	df = filter_weekends(df)

	## Candle Change
	df['Change'] = (df.Close - df.Open) / df.Open

	print('Here')

	## Body Range Pct
	df['BRP'] = abs(df.Close - df.Open) / (df.High - df.Low)

	## High Body Pct
	df['HBP'] = (df.High - df[['Open', 'Close']].max(axis=1)) / (df.High - df[['Open', 'Close']].min(axis=1))

	## Low Body Pct
	df['LBP'] = (df[['Open', 'Close']].min(axis=1) - df.Low) / (df[['Open', 'Close']].max(axis=1) - df.Low)

	## Distribution Statistics
	df['STDLong'] = df.Change.rolling(window=long_window, min_periods=1).std()
	df['STDShort'] = df.Change.rolling(window=short_window, min_periods=1).std()

	df['LongVol'] = df.STDLong/np.sqrt(long_window)
	df['ShortVol'] = df.STDShort/np.sqrt(short_window)

	# Add a small quantity to avoid -inf from the logarithm
	df.loc[:, 'LongVol'] = np.log(df.LongVol+1e-8)
	df.loc[:, 'ShortVol'] = np.log(df.ShortVol+1e-8)

	df['LongSkew'] = df.Change.rolling(window=long_window, min_periods=1).skew()
	df['ShortSkew'] = df.Change.rolling(window=short_window, min_periods=1).skew()

	df.loc[:, 'LongSkew'] = df.LongSkew.fillna(value=0)
	df.loc[:, 'ShortSkew'] = df.ShortSkew.fillna(value=0)

	#Positioning Indicators
	df['LongSMA'] = df.Close.rolling(window=long_window, min_periods=1).mean()
	df['ShortSMA'] = df.Close.rolling(window=short_window, min_periods=1).mean()

	df['DLongSMA'] = df.Close / df['LongSMA'].values
	df['DShortSMA'] = df.Close / df['ShortSMA'].values

	### Center Metrics Around 1
	for col in df.columns:
		if col in ['Open', 'High', 'Low', 'Close']:
			df[col] = df[col].pct_change() + 1

	# Market Sessions
	df = market_sessions(df)

	long_rolling_window = df.Change.rolling(window=long_window, min_periods=1)
	short_rolling_window = df.Change.rolling(window=short_window, min_periods=1)

	start = time.time()
	df['LongKurtosis'] = long_rolling_window.apply(kurtosis, raw=True)
	df['ShortKurtosis'] = short_rolling_window.apply(kurtosis, raw=True)

	df.loc[:, 'LongKurtosis'] = df.LongKurtosis.fillna(value=0)
	df.loc[:, 'ShortKurtosis'] = df.ShortKurtosis.fillna(value=0)
	print(time.time() - start, 'Kurtosis time')

	# Time series progressions
	start = time.time()
	df['LongProg'] = df.Close.rolling(window=long_window, min_periods=1).apply(cp, raw=True)
	df['ShortProg'] = df.Close.rolling(window=short_window, min_periods=1).apply(cp, raw=True)
	print(time.time() - start, 'Prog Time')

	# Approximate Entropy
	start = time.time()
	df['LongApproximateEntropy'] = long_rolling_window.apply(approx_entropy, raw=True)
	df['ShortApproximateEntropy'] = short_rolling_window.apply(approx_entropy, raw=True)
	print(time.time() - start, 'App Time')

	# Spectral Entropy
	start = time.time()
	df['LongSpectralEntropy'] = long_rolling_window.apply(spec_entropy, raw=True)
	df['ShortSpectralEntropy'] = short_rolling_window.apply(spec_entropy, raw=True)
	print(time.time() - start, 'Spec Time')

	# Autocorrelation
	start = time.time()
	df['LongAutocorrelation'] = long_rolling_window.apply(autocorrelation, raw=False)
	df['ShortAutocorrelation'] = short_rolling_window.apply(autocorrelation, raw=False)
	print(time.time() - start, 'Auto Time')

	# Stationarity
	start = time.time()
	df['LongStationarity'] = long_rolling_window.apply(stationarity, raw=True)
	df['ShortStationarity'] = short_rolling_window.apply(stationarity, raw=True)
	print(time.time() - start, 'Stat Time')

	# FILL NA
	df.LongSpectralEntropy.fillna(0, inplace=True)
	df.ShortSpectralEntropy.fillna(0, inplace=True)
	df.LongAutocorrelation.fillna(0, inplace=True)
	df.ShortAutocorrelation.fillna(0, inplace=True)
	df.LongApproximateEntropy.fillna(0, inplace=True)
	df.ShortApproximateEntropy.fillna(0, inplace=True)

	## Remove first 50
	df = df.iloc[long_window:, :]

	# Discard Temp Features
	df.drop(['Volume', 'LongSMA', 'ShortSMA', 'Open', 'High', 'Low', 'Close', 'STDLong', 'STDShort'], axis=1, inplace=True)

	## NaN Value Check
	print(df.isnull().sum(axis=0))

	print()

	print(df.head())

	df.to_csv(features_dir/ticker, index=False)

def get_tickers():

	tickers = []

	for file in os.listdir(data_dir):

		ticker = file.split('-')[0]
		tickers.append(ticker) if ticker not in tickers else None

	return tickers

def go_parallel():

	Parallel(n_jobs=n_jobs)(delayed(features)(ticker) for ticker in get_tickers())

def main(ticker):

	if ticker == 'ALL':
		go_parallel()
	else:
		features(ticker)

######################################################################

if __name__ == '__main__':

	argparse = ArgumentParser()
	argparse.add_argument('ticker')
	args = argparse.parse_args()

	main(args.ticker)