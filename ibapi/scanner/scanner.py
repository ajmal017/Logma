from apscheduler.schedulers.background import BackgroundScheduler
import joblib

from scanner.scanner_wrapper import ScannerWrapper
from scanner.scanner_client import ScannerClient

from datetime import datetime, timedelta
from collections import namedtuple
from threading import Thread
import queue, time

##############################

DataConfig = namedtuple('DataConfig', ['durationStr', 'barSizeSetting', 'whatToShow',
									   'useRTH', 'formatDate', 'keepUpToDate'])

##############################

class Scanner(ScannerClient, ScannerWrapper):

	def __init__(self, ip_address, port, clientId, ticker2id, id2ticker, contracts, tick_increments, num_periods, time_period):

		ScannerWrapper.__init__(self)
		ScannerClient.__init__(self, self)

		## Instrument configuration
		self.ticker2id = ticker2id
		self.id2ticker = id2ticker
		self.contracts = contracts
		self.tick_increments = tick_increments

		## Strategy configuration
		self.num_periods = num_periods
		self.time_period = time_period

		## Data storages
		self.storages = {}

		## Historical data configuration
		self.config = DataConfig(
				durationStr = "{} S".format(int(time_period * num_periods * 60)),
				barSizeSetting = "{} mins".format(time_period),
				whatToShow = "MIDPOINT",
				useRTH = 0,
				formatDate = 1,
				keepUpToDate = True
			)

		print('Config', self.config)

		print('Connecting')
		self.connect(ip_address, port, clientId)

		thread = Thread(target = self.run)
		thread.start()

	def on_start(self):

		## Initialize Storages for each ticker
		print('Initializing Historical Data')
		self.init_historical_data()

	def on_close(self):

		self.disconnect()

if __name__ == '__main__':

	scanner = Scanner(ip_address, port, clientId)