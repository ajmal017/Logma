import sys

sys.path.append('.')

from threading import Thread
from strategy import Strategy

class StrategyThread(Thread):

	def __init__(self):

		Thread.__init__(self)
		self.strategy = Strategy(num_periods = 50, short_num_periods = 20, time_period = 5)
		self.strategy.on_start()

	def on_close(self):

		self.strategy.on_close()
		self.join()
		print('Done')
