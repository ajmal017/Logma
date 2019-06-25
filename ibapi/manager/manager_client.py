from ibapi.client import EClient
from ibapi.order import Order

from tools.zcontracts import forex_contract
from tools.zorders import limit_order
from tools.utils import adjust_price
from tools.zlogging import loggers

from trade import Trade

import numpy as np
import queue, time

class ManagerClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def on_signal(self, direction, quantity, symbol, prices, data):

		loggers[symbol].info('Signal {} - Executing Trade'.format(direction))

		## Tick increment
		tick_increment = self.tick_increments[symbol]

		## Direction
		action = self.direction2action[direction]

		## Set up targets & adjust for tick increments
		open_, close = prices
		cs = abs(close - open_)

		entry = close
		entry = adjust_price(entry, tick_increment, direction, margin=2)

		take_profit = entry + (cs * direction)
		take_profit= adjust_price(take_profit, tick_increment, direction, margin=2)

		soft_stop = entry - (cs * self.risk * direction)
		soft_stop = adjust_price(soft_stop, tick_increment, direction, margin=0)

		hard_stop = entry - 2 * (cs * self.risk * direction)
		hard_stop = adjust_price(hard_stop, tick_increment, direction, margin=0)

		reduced_soft = entry - (cs * self.risk * 0.5 * direction)
		reduced_soft = adjust_price(reduced_soft, tick_increment, direction, margin=0)

		reduced_hard = entry - 2 * (cs * self.risk * 0.5 * direction)
		reduced_hard = adjust_price(reduced_hard, tick_increment, direction, margin=0)

		## Trade details
		details = {
			"entry_price" : entry,
			"take_profit" : take_profit,
			"soft_stop" : soft_stop,
			"hard_stop" : hard_stop,
			"reduced_soft" : reduced_soft,
			"reduced_hard" : reduced_hard,
			"candle_size" : cs / (tick_increment / 5)
		}

		## Add trade object to index
		self.trades[symbol] = Trade(manager = self, symbol = symbol, action = action, direction = direction, quantity = quantity, details = details, data = data)

		## Start market data for instrument
		self.reqMktData(self.ticker2id[symbol], self.contracts[symbol], '', False, False, [])

