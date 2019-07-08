import sys

sys.path.append('.')

from threading import Thread
from strategy import Strategy

class StrategyThread(Thread):

	def __init__(self, num_periods, short_num_periods, time_period):

		Thread.__init__(self)
<<<<<<< HEAD
		self.strategy = Strategy(num_periods = 50, short_num_periods = 20, time_period = 5)
=======
		self.strategy = Strategy(num_periods = num_periods, short_num_periods = short_num_periods, time_period = time_period)
>>>>>>> 6c273b56f4cc009cb640b3ec6ae477cb3c2d10b4
		self.strategy.on_start()

	def on_close(self):

		self.strategy.on_close()
		self.join()
		print('Done')
