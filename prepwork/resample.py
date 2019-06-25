import pandas as pd
import sys, os
import numpy as np
from argparse import ArgumentParser
from joblib import delayed	, Parallel

################################################

input_dir_ = 'D:/TickData_UZ_FW'
output_dir_ = 'D:/TickData_Agg_FW'

n_jobs = 12
min_ = 5

################################################

def vwap(data):
    x = data.value_counts(sort=False).reset_index().values
    p, q = x[:, 0], x[:, 1]
    return (p * (q / q.sum())).sum()

def resample_ticker(ticker):

	main = []

	for file in os.listdir(input_dir_):

		if file.split('-')[0] == ticker:
			
			print(file)
			df = pd.read_csv('{}/{}'.format(input_dir_, file), header=None, names=['Ticker', 'Datetime', 'Bid', 'Ask'])
			df['Datetime'] = pd.to_datetime(df.Datetime)
			df.set_index('Datetime', inplace=True)
			df['Price'] = (df['Bid'] + df['Ask'])/2

			df = df.resample('%dT' % min_).agg({
			    'Price' : [('Open', 'first'),  
			               ('High', 'max'),
			               ('Low', 'min'),
			               ('Close', 'last'), 
			               ('Volume', 'sum'),
			               ('Ticks', 'count'), 
			               ('VWAP', vwap)]
			}).bfill()
			df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Ticks', 'VWAP']

			print(df.head())

			main.append(df)
		
	main = pd.concat(main, axis=0)
	main.to_csv('{}/{}.csv'.format(output_dir_, ticker))

def get_tickers():

	tickers = []

	for file in os.listdir(input_dir_):

		ticker = file.split('-')[0]
		tickers.append(ticker) if ticker not in tickers else None

	return tickers

def go_parallel():

	Parallel(n_jobs=n_jobs)(delayed(resample_ticker)(ticker) for ticker in get_tickers())

def main(ticker):

	if ticker == 'ALL':

		go_parallel()

	else:

		resample_ticker(ticker)

if __name__ == '__main__':

	argparser = ArgumentParser()
	argparser.add_argument('ticker')
	args = argparser.parse_args()

	sys.exit(main(args.ticker))
