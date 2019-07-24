import pandas as pd
import numpy as np
import sys, os

from sklearn.model_selection import ParameterGrid
from sklearn.model_selection import StratifiedKFold

import lightgbm as lgbm
from sklearn.metrics import accuracy_score

import joblib
from joblib import delayed, Parallel

def evalerror(labels, preds):
	preds[preds > 0.5] = 1
	preds[preds <= 0.5] = 0
	return 'accuracy', accuracy_score(preds, labels), True

dir_ = 'res'

def get_main_df():

	main = []

	for file in os.listdir('D:/AlgoMLData/ScaledIB/'):
		print(file)
		ticker = file.split('_')[0]
		df = pd.read_csv('D:/AlgoMLData/ScaledIB/{}'.format(file))
		df['Ticker'] = ticker
		main.append(df)

	main = pd.concat(main, axis=0).reset_index(drop=True)

	print(main.head())
	print(main.columns)

	main.loc[main.TTC <= 20, 'TTC'] = 1
	main.loc[main.TTC > 20, 'TTC'] = 0

	main = main[(main.sig30 == 1) & (main.sig50 == 1)]

	print(main.TTC.sum() / main.shape[0])

	return main

def eval_fold(idct, idcv, X_train, y_train, param_grid, i):

	best_params = []

	xt, yt = X_train.values[idct, :], y_train[idct]
	xv, yv = X_train.values[idcv, :], y_train[idcv]
	
	for j, param in enumerate(ParameterGrid(param_grid)):
		
		gbm = lgbm.LGBMClassifier(objective='binary', **param)
		gbm = gbm.fit(xt, yt, eval_set=[(xv, yv)], eval_metric='auc',
					  early_stopping_rounds=10, verbose=250)

		key1 = list(gbm.best_score_)[0]
		best_params.append([param, gbm.best_score_[key1]['binary_logloss'], gbm.best_score_[key1]['auc']])

		print(j, '\n')

	with open('%s/results_%s.pkl' % (dir_,i), 'wb') as file:
		joblib.dump(best_params, file)

def go_parallel():

	np.random.seed(72)

	main = get_main_df()
	print(main.TTC.value_counts())

	train_pct = 0.5
	test_pct = 1 - train_pct
	idc = np.random.permutation(main.shape[0])
	train_len = int(train_pct * main.shape[0])

	## Partition the data
	train = main.iloc[idc[:train_len], :]
	test = main.iloc[idc[train_len:], :]

	##################
	## TRAIN SET
	##################

	y_train = train.TTC.values
	idx = train.columns.tolist().index('Direction')
	X_train = train.iloc[:, idx:-1]
	print(X_train.columns)

	##################
	## TEST SET
	##################

	y_test = test.TTC.values
	idx = test.columns.tolist().index('Direction')
	X_test = test.iloc[:, idx:-1]
	print(X_train.columns)

	print(X_train.head())
	print(X_test.head())

	####################
	## PARAMETER SEARCH
	####################

	NFOLDS = 5
	kfold = StratifiedKFold(n_splits=NFOLDS, shuffle=True, random_state=218)

	param_grid = {
		'n_estimators' : [10000],
		'max_depth' : [-1, 5, 10, 20, 50, 100],
		'learning_rate' : [0.0001, 0.001, 0.05, 0.1],
		'num_leaves' : [5, 10, 20, 50, 100],
		'min_child_weight' : [0.0001, 0.001, 0.05, 0.1],
	}
	print('Num Searches', len(list(ParameterGrid(param_grid))) * 5)

	Parallel(n_jobs=5)(delayed(eval_fold)(idct, idcv, X_train, y_train, param_grid, i)
					for i, (idct, idcv) in enumerate(kfold.split(X_train, y_train)))

if __name__ == '__main__':

	go_parallel()

