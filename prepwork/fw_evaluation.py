import json, joblib

import pandas as pd
import numpy as np

import sys, os

import matplotlib.pyplot as plt
import seaborn as sns

stats = {}

for file in os.listdir('D:/TickData_Agg_FW'):

	print(file)
	ticker = file[:-4]
	features = pd.read_csv(f'D:/AlgoMLData/Features_FW/{ticker}_clean.csv')
	trades = pd.read_csv(f'D:/AlgoMLData/AddTrades_FW/{ticker}_trades.csv')

	unique_dts = features.Datetime.value_counts()
	unique_dts = unique_dts[unique_dts == 1].index.values
	trades = trades[trades.Datetime.isin(unique_dts)]
	trades = trades.merge(features, how='outer', on='Datetime').dropna()


	with open(f'D:/AlgoMLData/Scalers/{ticker}', 'rb') as file:
		scaler = joblib.load(file)

	def log_trimming(x):
		cutoff_lt, cutoff_gt = -5, 5
		try:
			x[x > cutoff_gt] = cutoff_gt + np.log(x - cutoff_gt + 1)
		except:
			pass
		try:
			x[x < cutoff_lt] = cutoff_lt - np.log(abs(x) - abs(cutoff_lt) + 1)
		except:
			pass
		return x

	def iqr_trimming(x, feature):

		lower_fence, upper_fence = scaler[feature]
		
		try:
			x[x > upper_fence] =  upper_fence + x/100
		except:
			pass
		try:
			x[x < lower_fence] =  lower_fence - x/100
		except:
			pass
		
		return x

	## IQR Trimming

	# Change
	trades.loc[:, 'Change'] = iqr_trimming(trades.Change.values, 'change')

	# DLongSMA
	trades.loc[:, 'DLongSMA'] = iqr_trimming(trades.DLongSMA.values, 'dlongsma')

	# DShortSMA
	trades.loc[:, 'DShortSMA'] = iqr_trimming(trades.DShortSMA.values, 'dshortsma')

	# LongProg
	trades.loc[:, 'LongProg'] = iqr_trimming(trades.LongProg.values, 'longprog')

	# ShortProg
	trades.loc[:, 'ShortProg'] = iqr_trimming(trades.ShortProg.values, 'shortprog')

	# Short Approximate Entropy
	trades.loc[:, 'ShortApproximateEntropy'] = iqr_trimming(trades.ShortApproximateEntropy.values, 'shortappentropy')

	# Long Approximate Entropy
	trades.loc[:, 'LongApproximateEntropy'] = iqr_trimming(trades.LongApproximateEntropy.values, 'longappentropy')

	# Long Spectral Entropy
	trades.loc[:, 'LongSpectralEntropy'] = iqr_trimming(trades.LongSpectralEntropy.values, 'longspecentropy')

	### SCALING
	drop = ['ShortSpectralEntropy']
	no_scale = ['LongStationarity', 'ShortStationarity', 'Asia', 'Amer', 'Eur']


	cols = [col for col in features.columns if col not in drop+no_scale+['Datetime']]
	X_scale = trades[cols]
	X_scale = scaler['ss'].transform(X_scale)
	trades.loc[:, cols] = X_scale

	trades['Change'] = log_trimming(trades.Change.values.copy())

	trades['LongProg'] = log_trimming(trades.LongProg.values.copy())
	trades['ShortProg'] = log_trimming(trades.ShortProg.values.copy())

	trades['DLongSMA'] = log_trimming(trades.DLongSMA.values.copy())
	trades['DShortSMA'] = log_trimming(trades.DShortSMA.values.copy())

	trades['ShortApproximateEntropy'] = log_trimming(trades.ShortApproximateEntropy.values.copy())
	trades['LongApproximateEntropy'] = log_trimming(trades.LongApproximateEntropy.values.copy())

	trades['LongSpectralEntropy'] = log_trimming(trades.LongSpectralEntropy.values.copy())

	trades.drop(['ShortSpectralEntropy'], axis=1, inplace=True)


	from sklearn.metrics import accuracy_score
	with open('../models/lgbm_2019-06-16', 'rb') as file:
		predictor = joblib.load(file)

	## Binarize the TTC Feature
	trades['YTest'] = (trades.TTC <= 20).astype(int)
	X_test = trades.iloc[:, 3:-1].copy()

	y_pred = predictor.predict(X_test)

	acc_score = accuracy_score(trades.YTest, y_pred)
	print('Accuracy', acc_score)

	trades = trades[y_pred == 1]
	raw = pd.read_csv(f'D:/TickData_Agg_FW/{ticker}.csv')

	last_idx = -1
	num_tint = 0
	pnl = []
	trade_lengths = []

	for datetime, ttc, direction in zip(trades.Datetime, trades.TTC.astype(int), trades.Direction):
		
		idx = raw[raw.Datetime == datetime].index.values[0]
		
		print(datetime, ttc, direction, last_idx, idx)
		
		if idx < last_idx:
			num_tint += 1
			print(last_idx)
			print(idx)
			continue
		
		
		tmp = raw.iloc[idx:idx+ttc+1]

		if tmp.shape[0] == 0:
			continue

		tmp['Change'] = abs(tmp.Close - tmp.Open)
		cs = tmp.Change.values[0]
		max_risk = cs * 2.5
		tmp['Anchor'] = tmp.Close.values[0]
		tmp['RDD'] = direction * (tmp.Close - tmp.Anchor)
		tmp['MaxRisk'] = -max_risk
		
		x = tmp[tmp.RDD < -max_risk]
		if x.shape[0] != 0:
			trade_lengths.append(x.index.values[0] - idx)
			idx = x.index.values[0]
			pnl.append(x.RDD.values[0])
			last_idx = idx
		else:
			trade_lengths.append(ttc)
			pnl.append(cs)
			last_idx = tmp.index.values[-1]


	pnl = np.array(pnl)
	success = pnl.copy()
	success = success[success > 0].shape[0] / len(success)
	print('Success Rate', success)

	plt.figure(figsize=(20, 16))
	sns.barplot(np.arange(len(pnl)), pnl)
	plt.savefig(f'D:/Plots/{ticker}_plot.png')

	stats[ticker] = {
		'success' : success,
		'accuracy' : acc_score,
		'pnl' : pnl,
		'trade_lengths' : trade_lengths,
		'trade_in_trade': num_tint
	}

with open('D:/AlgoMLData/fw_stats', 'wb') as file:
	joblib.dump(stats, file)
