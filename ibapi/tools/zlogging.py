from elasticsearch import Elasticsearch, helpers
from datetime import datetime
import logging
import os

dir_ = os.path.dirname(os.path.realpath(__name__))
es = Elasticsearch([{"host" : "localhost", "port" : 9200}])

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

#### LOGGING ####

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

#### INDEXING ######

fmt = '%Y-%m-%dT%H:%M:%S'
es = Elasticsearch([{"host" : "192.168.2.38", "port" : 9200}])

def post_doc(trade):

	trades.data['dates'] = [x[0] for x in trade.data['historical']]
	trade.data['historical'] = [x[1:] for x in trade.data['historical']]

	doc_ = {
		"ticker" : trade.symbol,
		"action" : trade.action,
		"initTime" : trade.init_time.strftime(fmt),
		"direction" : 1 if trade.action == "BUY" else -1
		"state" : trade.state,
		"status" : trade.status,
		"data" : trade.data,
		"entryLimitPrice" : trade.orders.init_order.lmtPrice,
		"takeProfitLimitPrice" : trade.orders.profit_order.lmtPrice,
		"stopLossLimitPrice" : trade.orders.loss_order.lmtPrice,
		"timePeriod" : trade.time_period,
		"maturity" : trade.maturity,
		"numPeriods" : len(trade.data['historical'])
		"executionLogic" : trade.execution_logic,
		"tickIncrement" : trade.tick_incr
	}

	if trade.status != 'PENDING':

		doc_['position'] = trade.num_filled
		doc_['avgCost'] = trade.avg_filled_price
		doc_['positionClosed'] = trade.num_filled_on_close
		doc_['avgCostOnClose'] = trade.avg_filled_price_on_close
		doc_['executionTime'] = trade.execution_time.strftime(fmt)
		doc_['drawdown'] = trade.drawdown
		doc_['runUp'] = trade.run_up
		doc_['closingTime'] = datetime.now().strftime(fmt)

	doc_ = {
		"_index" : "trades",
		"_type" : "retracement",
		"_source" : doc_
	}

	helpers.bulk(es, [doc_])
