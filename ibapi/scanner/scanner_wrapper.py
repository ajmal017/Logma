from ibapi.wrapper import EWrapper
from tools.zlogging import loggers

from datetime import datetime
import queue

import numpy as np
import pandas as pd

class ScannerWrapper(EWrapper):

	def error(self, id_, error_code, error_msg):
		msg = '{}~-~{}~-~{}'.format(id_, error_code, error_msg)
		loggers['error'].info(msg)

	def historicalData(self, reqId, bar):
		ticker = self.id2ticker[reqId]
		self.storages[ticker].append(bar)

	def historicalDataUpdate(self, reqId, bar):
		ticker = self.id2ticker[reqId]
		self.storages[ticker].update(bar)
