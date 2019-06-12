from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timedelta
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
	file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d  %H:%M:%S'))

	logger.addHandler(file_handler)

	loggers[ticker] = logger

logger = logging.getLogger('errors')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('{}/{}/{}.log'.format(dir_, 'logs', 'errors'), 'w')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d  %H:%M:%S'))

logger.addHandler(file_handler)

loggers['error'] = logger

#### INDEXING ######

fmt = '%Y-%m-%dT%H:%M:%S'
es = Elasticsearch([{"host" : "localhost", "port" : 9200}])

actions = []

def post_market_data_doc(ticker, time_period, data_time, data_type, data, dates = None):

	dt = datetime.now()
	dt -= timedelta(minutes = dt.minute % time_period)

	if type(data_time) == str:
		data_time = datetime.strptime(data_time, '%Y%m%d  %H:%M:%S').strftime(fmt)
	else:
		data_time = (datetime.utcfromtimestamp(data_time) - timedelta(hours=4)).strftime(fmt)

	data = {
		"historical" : data,
	}
	if dates is not None:
		data['dates'] = dates

	doc_ = {
		"ticker" : ticker,
		"candleTime" : dt.strftime(fmt),
		"dataTime" : data_time,
		"dataType" : data_type,
		"data" : data
	}

	doc_ = {
		"_index" : "marketdata",
		"_type" : "_doc",
		"_source" : doc_
	}

	actions.append(doc_)

	## Aliasing with our 5 minute time frame
	if len(actions) % 107 == 0:

		try:
			helpers.bulk(es, [doc_])
		except Exception as e:
			loggers['error'].info(e)

		actions = []

def post_trade_doc(trade):

	trade.data['dates'] = [x[0] for x in trade.data['historical']]
	trade.data['historical'] = [x[1:] for x in trade.data['historical']]

	doc_ = {
		"ticker" : trade.symbol,
		"action" : trade.action,
		"initTime" : trade.init_time.strftime(fmt),
		"direction" : 1 if trade.action == "BUY" else -1,
		"state" : trade.state,
		"status" : trade.status,
		"data" : trade.data,
		"entryLimitPrice" : trade.orders['init']['order'].lmtPrice,
		"takeProfitLimitPrice" : trade.orders['profit']['order'].lmtPrice,
		"stopLossLimitPrice" : trade.orders['loss']['order'].lmtPrice,
		"timePeriod" : trade.time_period,
		"maturity" : trade.maturity,
		"numPeriods" : len(trade.data['historical']),
		"executionLogic" : trade.execution_logic,
		"tickIncrement" : trade.tick_incr,
		"numUpdates" : trade.num_updates
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
		"_index" : "retracements",
		"_type" : "_doc",
		"_source" : doc_
	}

	try:
		helpers.bulk(es, [doc_])
	except Exception as e:
		loggers['error'].info(e)
