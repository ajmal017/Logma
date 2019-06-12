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

	def init_data(self):

		for ticker, contract in self.contracts.items():

			loggers[ticker].info('Initializing historical data')

			self.instruments[ticker].storage = Storage(ticker = ticker, num_periods = self.num_periods, time_period = self.time_period, scanner_job = self.instruments[ticker].scanner_job)
			reqId = self.ticker2id[ticker]
			self.reqHistoricalData(reqId, contract, datetime.now().strftime('%Y%m%d %H:%M:%S'), *self.config, [])

	def cancel_data(self):

		for ticker in self.contracts:

			reqId = self.ticker2id[ticker]
			self.cancelRealTimeBars(reqId)