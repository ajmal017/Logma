from ibapi.wrapper import EWrapper
from tools.zlogging import loggers

from datetime import datetime
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

			self.cancel_historical_data()
			self.disconnect()

			time.sleep(1)

			self.connect(*self.connection)
			self.init_historical_data()

			## Repoint with fresh data
			for ticker in self.instruments:
				self.instruments[ticker].storage = self.storages[ticker]
				self.instruments[ticker].blocker.resume_job('scanner_job')

	def historicalData(self, reqId, bar):
		ticker = self.id2ticker[reqId]
		self.storages[ticker].append(bar)

	def historicalDataUpdate(self, reqId, bar):
		ticker = self.id2ticker[reqId]
		self.storages[ticker].update(bar)
