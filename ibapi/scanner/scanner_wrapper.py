from ibapi.wrapper import EWrapper
from tools.zlogging import loggers

from datetime import datetime, timedelta
import queue, time

import numpy as np
import pandas as pd

class ScannerWrapper(EWrapper):

	def error(self, reqId, error_code, error_msg):
		msg = '{}~-~{}~-~{}'.format(reqId, error_code, error_msg)
		loggers['error'].info(msg)

		if error_code == 1100 and self.state == 'ALIVE':

			loggers['error'].warning("Scanner Connection Lost - Waiting for reconnection message")

			self.state = "DEAD"

			for ticker in self.instruments:
				self.instruments[ticker].blocker.pause_job('scanner_job')

		elif (error_code == 1102 or error_code == 1101) and self.state == "DEAD":

			loggers['error'].warning("Scanner Connection Regained - Waiting for initialization")

			self.state = "ALIVE"

			self.cancel_data()
			self.disconnect()

			time.sleep(1)

			self.connect(*self.connection)
			self.init_data()

			## Repoint with fresh data
			for ticker in self.instruments:
				self.instruments[ticker].storage = self.storages[ticker]
				self.instruments[ticker].blocker.resume_job('scanner_job')

	def historicalData(self, reqId, bar):

		ticker = self.id2ticker[reqId]
		self.storages[ticker].data.append((bar.date, bar.open, bar.high, bar.low, bar.close))

	def historicalDataEnd(self, reqId, start, end):

		ticker = self.id2ticker[reqId]
		storage = self.storages[ticker]

		storage.current_candle_time = storage.candle_time()
		storage.current_candle = storage.data[49]

		self.reqRealTimeBars(reqId, self.contracts[ticker], 5, "MIDPOINT", False, [])

	def realtimeBar(self, reqId, date, open_, high, low, close, volume, WAP, count):

		ticker = self.id2ticker[reqId]
		storage = self.storages[ticker]

		date = (datetime.utcfromtimestamp(date) - timedelta(hours=4)).strftime("%Y%m%d  %H:%M:00")
		storage.update((date, open_, high, low, close))
