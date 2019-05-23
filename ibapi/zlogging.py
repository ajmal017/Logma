import logging
import os

dir_ = os.path.dirname(os.path.realpath(__name__))

tickers = [	"EURCHF",
			"USDCHF",
			"GBPUSD",
			"USDJPY",
			"EURUSD",
			"EURGBP",
			"NZDUSD",
			"USDCAD",
			"EURJPY",
			"AUDUSD",
			"GBPJPY",
			"CHFJPY",	
			"AUDNZD",
			"CADJPY"]

loggers = {}

for ticker in tickers:

	logger = logging.getLogger(ticker)
	logger.setLevel(logging.INFO)

	file_handler = logging.FileHandler('{}/{}/{}.log'.format(dir_, 'logs', ticker), 'w')
	file_handler.setLevel(logging.INFO)
	file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s\n', datefmt='%Y-%m-%d  %H:%M:%S'))

	logger.addHandler(file_handler)

	loggers[ticker] = logger

logger = logging.getLogger('errors')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('{}/{}/{}.log'.format(dir_, 'logs', 'errors'), 'w')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s\n', datefmt='%Y-%m-%d  %H:%M:%S'))

logger.addHandler(file_handler)

loggers['error'] = logger
