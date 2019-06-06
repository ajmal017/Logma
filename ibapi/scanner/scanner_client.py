from ibapi.client import EClient
from tools.zcontracts import forex_contract
from tools.zlogging import loggers
from storage import Storage

from datetime import datetime, timedelta
import time

import pandas as pd
import queue

class ScannerClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def init_historical_data(self):

		for ticker, contract in self.contracts.items():

			loggers[ticker].info('Initializing historical data')

			self.storages[ticker] = Storage(ticker = ticker, num_periods = self.num_periods, time_period = self.time_period)
			reqId = self.ticker2id[ticker]
			self.reqHistoricalData(reqId, contract, '', *self.config, [])

		time.sleep(1)

		initialized = True
		for ticker in self.storages:
			initialized = self.storages[ticker].is_initialized() and initialized

		if not initialized:
			loggers['error'].warning('Re-initializing.')
			self.cancel_historical_data()
			time.sleep(1)
			return self.init_historical_data()

	def cancel_historical_data(self):

		for ticker in self.contracts:

			loggers[ticker].info('Cancelling historical data.')
			
			reqId = self.ticker2id[ticker]
			del self.storages[ticker]		
			self.cancelHistoricalData(reqId)