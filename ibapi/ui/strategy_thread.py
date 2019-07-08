import sys

sys.path.append('.')

from threading import Thread
from strategy import Strategy

class StrategyThread(Thread):

	def __init__(self, num_periods, short_num_periods, time_period):

		Thread.__init__(self)
		self.strategy = Strategy(num_periods = num_periods, short_num_periods = short_num_periods, time_period = time_period)
		self.strategy.on_start()

	def on_close(self):

		self.strategy.on_close()
		self.join()
		print('Done')
