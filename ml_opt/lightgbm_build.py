import pandas as pd
import numpy as np
import sys, os

from sklearn.model_selection import ParameterGrid
from sklearn.model_selection import StratifiedKFold

import lightgbm as lgbm
from sklearn.metrics import accuracy_score

import joblib
from joblib import delayed, Parallel

from datetime import datetime

dir_ = 'res'

def get_main_df():

	main = []

	for file in os.listdir('D:/AlgoMLData/Scaled/'):
		print(file)
		ticker = file.split('_')[0]
		df = pd.read_csv('D:/AlgoMLData/Scaled/{}'.format(file))
		df['Ticker'] = ticker
		main.append(df)

	main = pd.concat(main, axis=0).reset_index(drop=True)

	main.loc[main.TTC <= 20, 'TTC'] = 1
	main.loc[main.TTC > 20, 'TTC'] = 0

	main = main[(main.sig30 == 1) & (main.sig50 == 1)]

	print(main.TTC.sum() / main.shape[0])

	return main

def main():

	np.random.seed(72)

	main = get_main_df()
	print(main.TTC.value_counts())

	train_pct = 0.5
	test_pct = 1 - train_pct
	validation_pct = 0.2 ## I Use 5 folds to build it.
	idc = np.random.permutation(main.shape[0])
	train_len = int(train_pct * main.shape[0])

	## Partition the data
	train = main.iloc[idc[:train_len], :]
	test = main.iloc[idc[train_len:], :]

	##################
	## TRAIN & VAL SET
	##################

	y_train = train.TTC.values
	idx = train.columns.tolist().index('Direction')
	## Remove the tickers from the last column
	X_train = train.iloc[:, idx:-1]
	print(X_train.columns)

	idc = np.random.permutation(X_train.shape[0])
	pct = int(0.2*X_train.shape[0])
	idc_train = idc[pct:]
	idc_val = idc[:pct]
	X_val, y_val = X_train.values[idc_val, :], y_train[idc_val]
	X_train, y_train = X_train.values[idc_train, :], y_train[idc_train]

	##################
	## TEST SET
	##################

	y_test = test.TTC.values
	idx = test.columns.tolist().index('Direction')
	## Remove the tickers from the last column
	X_test = test.iloc[:, idx:-1]
	print(X_test.columns)

	## Save the testing set for the risk management portion
	with open('D:/AlgoMLData/Risk/lgbm_test_set', 'wb') as file:
		joblib.dump(test, file)

	##################
	## Build the model
	##################

	gbm = lgbm.LGBMClassifier(
	    num_leaves=20,
	    max_depth=5,
	    learning_rate=0.1,
	    min_child_weight=0.0001,
	    n_estimators=10000
	)

	gbm = gbm.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric='auc', early_stopping_rounds=50)
	y_pred = gbm.predict_proba(X_test)

	print('Testing .. {} Trades .. Accuracy : {}'.format(X_train.shape[0], accuracy_score(y_pred.argmax(axis=1), y_test)))

	## Save Model
	with open('../models/lgbm_{}'.format(datetime.now().strftime('%Y-%m-%d')), 'wb') as file:
		joblib.dump(gbm, file)

	## Reload model and predict on same set. 
	with open('../models/lgbm_{}'.format(datetime.now().strftime('%Y-%m-%d')), 'rb') as file:
		gbm = joblib.load(file)

	## Check model accuracy
	y_pred = gbm.predict(X_test)
	print('Testing/Reloading .. {} Trades .. Accuracy : {}'.format(X_train.shape[0], accuracy_score(y_pred, y_test)))

if __name__ == '__main__':

	main()

