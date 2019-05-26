from ibapi.client import EClient
from tools.zcontracts import forex_contract
from tools.zlogging import loggers
from storage import Storage

from datetime import datetime
import time

import pandas as pd
import queue

class ScannerClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def init_historical_data(self):

		print('Waiting for next minute')
		dt = datetime.now()
		while dt.second != 0:
			dt = datetime.now()

		for ticker, contract in self.contracts.items():

			self.storages[ticker] = Storage(ticker = ticker, num_periods = self.num_periods, time_period = self.time_period)
			reqId = self.ticker2id[ticker]
			loggers[ticker].info('Initializing historical data')		
			self.reqHistoricalData(reqId, contract, '', *self.config, [])

		time.sleep(5)

		initialized = True
		for ticker in self.storages:
			initialized = self.storages[ticker].is_initialized()

		if not initialized:
			self.cancel_historical_data()
			time.sleep(1)
			return self.init_historical_data()

	def cancel_historical_data(self):

		for ticker in self.contracts:
			loggers[ticker].info('Error. Cancelling historical data')
			reqId = self.ticker2id[ticker]
			del self.storages[ticker]		
			self.cancelHistoricalData(reqId)

		print(self.storages)