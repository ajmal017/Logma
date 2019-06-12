from ibapi.wrapper import EWrapper
from tools.zlogging import loggers, post_market_data_doc

from datetime import datetime, timedelta
import queue, time

import numpy as np
import pandas as pd

class ScannerWrapper(EWrapper):

	def error(self, reqId, error_code, error_msg):
		msg = '{}~-~{}~-~{}'.format(reqId, error_code, error_msg)
		loggers['error'].info(msg)

		if (error_code == 1100 or error_code == 2105) and self.state == 'ALIVE':

			loggers['error'].warning("Scanner Connection Lost - Waiting for reconnection message")

			self.state = "DEAD"

			## Pause all trades from initiating
			for ticker in self.instruments:
				self.instruments[ticker].state = "PAUSED"

		elif (error_code == 1102 or error_code == 1101 or error_code == 2106) and self.state == "DEAD":

			loggers['error'].warning("Scanner Connection Regained - Waiting for initialization")

			self.state = "ALIVE"

			self.cancel_data()
			self.disconnect()

			time.sleep(1)

			self.connect(*self.connection)
			self.init_data()

	def historicalData(self, reqId, bar):

		ticker = self.id2ticker[reqId]
		self.instruments[ticker].storage.data.append((bar.date, bar.open, bar.high, bar.low, bar.close))

	def historicalDataEnd(self, reqId, start, end):

		ticker = self.id2ticker[reqId]
		storage = self.instruments[ticker].storage

		storage.current_candle_time = storage.candle_time()
		storage.current_candle = storage.data[49]

		self.instruments[ticker].state = "ACTIVE"
		self.reqRealTimeBars(reqId, self.contracts[ticker], 5, "MIDPOINT", False, [])

		print('HistDataEnd', storage.current_candle)

		## Logging
		data = [tuple(row[1:]) for row in storage.data]
		dates = [row[0] for row in storage.data]

		post_market_data_doc(ticker, self.time_period, storage.current_candle[0], 'initCandle',
                             [tuple(row[1:]) for row in storage.data], dates)

	def realtimeBar(self, reqId, date, open_, high, low, close, volume, WAP, count):

		ticker = self.id2ticker[reqId]
		storage = self.instruments[ticker].storage
		storage.update((date, open_, high, low, close))
