from ibapi.client import EClient
from ibapi.order import Order

from zcontracts import forex_contract
from zorders import limit_order
from utils import adjust_price

from trade import Trade

import numpy as np
import queue, time

class ManagerClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def on_signal(self, direction, quantity, symbol, price):

		## Tick increment
		tick_increment = self.tick_increments[symbol]

		## Direction
		action = self.direction2action[action]

		## Adjust the price for min tick increment rule
		price = adjust_price(price, tick_increment, direction, margin = 1)

		## Trade details
		details = {
			"entry_price" : price
			"take_profit" : price + (direction * tick_increment * 4),
			"soft_stop" : price - (direction * tick_increment * 4),
			"hard_stop" : price - (direction * tick_increment * 8)
		}

		## Add trade object to index
		self.trades[symbol] = Trade(manager = self, symbol = symbol, action = action,
					  				initial_order = initial_order, closing_details = closing_details)

		## Request Live Quotes
		self.reqMarketDataType(1)

		## Start market data for instrument
		self.reqMktData(self.ticker_ids[symbol], contract, '', False, False, [])

