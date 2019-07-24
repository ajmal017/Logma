from joblib import delayed, Parallel

from zhistorical import zHistorical

tickers = [	"EURCHF","USDCHF","GBPUSD","USDJPY","EURUSD","EURGBP",
			"NZDUSD","USDCAD","EURJPY","AUDUSD","GBPJPY","CHFJPY",	
			"AUDNZD","CADJPY"]

def get_ticker(ticker, i):
	print(ticker)
	h = zHistorical(ticker[:3], ticker[3:], i)
	h.request_historical()

if __name__ == '__main__':

	Parallel(n_jobs=14)(delayed(get_ticker)(ticker, i) for i, ticker in enumerate(tickers))