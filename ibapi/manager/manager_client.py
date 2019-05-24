from ibapi.client import EClient
from ibapi.order import Order

from zcontracts import forex_contract
from zorders import limit_order
from utils import adjust_price
from zlogging import loggers

from trade import Trade

import numpy as np
import queue, time

class ManagerClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def on_signal(self, direction, quantity, symbol, price, data):

		loggers[symbol].info('Signal {} - Executing Trade'.format(direction))

		## Tick increment
		tick_increment = self.tick_increments[symbol]

		## Direction
		action = self.direction2action[direction]

		## Adjust the price for min tick increment rule
		price = adjust_price(price, tick_increment, direction, margin = 1)

		## Trade details
		details = {
			"entry_price" : price,
			"take_profit" : price + (direction * tick_increment * 1),
			"soft_stop" : price - (direction * tick_increment * 1),
			"hard_stop" : price - (direction * tick_increment * 2)
		}

		## Add trade object to index
		self.trades[symbol] = Trade(manager = self, symbol = symbol, action = action, direction = direction, quantity = quantity, details = details, data = data)

		## Request Live Quotes
		self.reqMarketDataType(1)

		## Start market data for instrument
		self.reqMktData(self.ticker2id[symbol], self.contracts[symbol], '', False, False, [])

