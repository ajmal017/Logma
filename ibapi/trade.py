from copy import deepcopy
from datetime import datetime
from tools.zorders import limit_order, limit_if_touched
from tools.utils import adjust_price
from tools.zlogging import loggers, post_trade_doc

from collections import namedtuple

TradeOrders = namedtuple('TradeOrders', ['init_order', 'init_oid', 'profit_order', 'profit_oid', 'loss_order', 'loss_oid'])

class Trade(object):

	def __init__(self, manager, symbol, action, direction, quantity, details, data):

		## Start Time
		self.init_time = datetime.now()

		## Book keeping
		self.symbol = symbol
		self.contract = manager.contracts[symbol]
		self.direction = direction
		self.action = action
		self.closing_action = manager.closing_actions[action]
		self.num_updates = []
		self.data = data

		## Manager stuff
		self.manager = manager
		self.tick_incr = manager.tick_increments[self.symbol]

		## Closing instructions
		self.details = details

		## Trade status
		self.status = 'PENDING'
		self.state = 'NORMAL'
		self.execution_logic = 'NONE'

		## Initial order quantity
		self.quantity = quantity

		## Place initial order
		self.setup()

		## Switches
		self.wick_switch = True
		self.maturity_switch = True
		self.soft_stop_switch = False
		self.take_profit_switch = False
		self.hard_stop_switch = False

		## Placeholders
		self.num_filled = 0
		self.num_filled_on_close = 0
		self.drawdown = 0
		self.run_up = 0
		self.avg_filled_price_on_close = -1
		self.avg_filled_price = -1
		self.execution_time = -1

		## Period details
		self.time_period = 5
		self.maturity = 20

		self.logger = loggers[symbol]

	def simple_view(self):

		return deepcopy({
			"Ticker" : self.symbol,
			"Initiated Time" : self.init_time,
			"Execution Time" : self.execution_time,
			"Direction" : int(self.direction),
			"Trade Length" : len(self.num_updates),
			"Status" : self.status,
			"State" : self.state,
			"Execution Logic" : self.execution_logic,
			"Quantity" : self.quantity,
			"Drawdown" : self.drawdown,
			"Run Up" : self.run_up,
			"Filled Position" : self.num_filled,
			"Avg Filled Price" : self.avg_filled_price,
			"Take Profit Price" : self.details['take_profit'],
			"Soft Stop Price" : self.details['soft_stop'],
			"Hard Stop Price" : self.details['hard_stop'],
			"Last Update" : getattr(self, 'last_update', 0),
			"Candle Size" : self.details['candle_size']
		})

	def setup(self):

		self.orders = {
			"init" : {
				"order" : None,
				"order_id" : None
			},
			"profit" : {
				"order" : None,
				"order_id" : None
			},
			"loss" : {
				"order" : None,
				"order_id" : None
			}
		}

		## Initial order
		init_order = limit_order(action = self.action, quantity = self.quantity, 
								 price = self.details['entry_price'], purpose = 'initiate', 
								 key = 'init')
		init_oid = self.manager.get_oid()
		self.manager.placeOrder(init_oid, self.contract, init_order)

		## Book keeping
		self.orders['init']['order_id'] = init_oid
		self.orders['init']['order'] = init_order
		self.manager.orders[init_oid] = init_order
		self.manager.order2trade[init_oid] = self

		## Take profit order
		profit_order = limit_order(action = self.closing_action, quantity = self.quantity,
								   price = self.details['take_profit'], purpose = 'close', 
								   key = 'profit')
		self.orders['profit']['order'] = profit_order

		## Stop loss order
		loss_order = limit_order(action = self.closing_action, quantity = self.quantity,
								   price = self.details['hard_stop'], purpose = 'close',
								   key = 'loss')
		self.orders['loss']['order'] = loss_order

		print('Init', self.symbol, init_oid)

	def on_fill(self):

		if self.status == 'PENDING':
			## Set trade status
			self.status = 'ACTIVE'
			self.execution_time = datetime.now()

			## Book keeping
			self.orders['profit']['order_id'] = profit_oid
			self.manager.orders[profit_oid] = self.orders['profit']['order']
			self.manager.order2trade[profit_oid] = self

			print('Filled', self.symbol)

	def on_close(self):

		if self.status in ['PENDING', 'ACTIVE']:

			print('CLOSING', self.symbol)
			## Cancel market data
			self.manager.cancelMktData(self.manager.ticker2id[self.symbol])

			## Logging
			self.logger.info('CLOSING LOGIC: {}'.format(self.execution_logic))

			for key in self.orders.keys():
				oid = self.orders[key]['order_id']
				if oid is not None:
					del self.manager.order2trade[oid]
					del self.manager.orders[oid]
					self.manager.cancelOrder(oid)

			# Remove trade from list
			del self.manager.trades[self.symbol]

			## Logging
			post_trade_doc(self)
			print('POSTED')

			self.status = 'CLOSED'

	def update_and_send(self, order_key, adjusted_price):
		
		self.orders[order_key]['order'].lmtPrice = adjusted_price
		#self.orders[order_key]['order'].totalQuantity = self.quantity - self.num_filled_on_close

		oid = self.orders[order_key]['order_id']
		oid = oid if oid is not None else self.manager.get_oid()
		self.manager.placeOrder(oid, self.contract, self.orders[order_key]['order'])

		## Book keeping
		self.orders[order_key]['order_id'] = oid
		self.manager.orders[oid] = self.orders[order_key]['order']
		self.manager.order2trade[oid] = self

	def on_event(self, order_key, margin = 1):

		adjusted_price = adjust_price(self.last_update, self.tick_incr, self.direction, margin = 1)
		## Send if not sent before
		if self.orders[order_key]['order_id'] is None:
			self.update_and_send(order_key, adjusted_price)
		## Chase the price to exit
		elif self.orders[order_key]['order'].lmtPrice != adjusted_price:
			self.update_and_send(order_key, adjusted_price)

	def on_period(self):

		## Log the number of updates per minute
		dt = (datetime.now() - self.init_time)
		idx = int(dt.seconds / 60)

		try:
			self.num_updates[idx] += 1
		except:
			self.num_updates.append(1)
		
		## If the trade was filled
		if self.status == 'ACTIVE':

			## Reduce the risk on events
			## On maturity
			if self.maturity_switch and self.is_matured():
				self.logger.info('MATURITY State reached.')
				self.state = 'MATURITY'
				self.details['soft_stop'] = self.details['reduced_soft']
				self.details['hard_stop'] = self.details['reduced_hard']
				self.maturity_switch = False

			## On wick in profit
			if self.wick_switch and self.is_in_profit():
				self.logger.info('WICK State reached.')
				self.state = 'WICK'
				self.details['soft_stop'] = self.details['reduced_soft']
				self.details['hard_stop'] = self.details['reduced_hard']
				self.wick_switch = False

			## Calculate drawdown/runup
			self.drawdown = min(self.direction * (self.last_update - self.avg_filled_price), self.drawdown)
			self.run_up = max(self.direction * (self.last_update - self.avg_filled_price), self.run_up)

			if self.is_take_profit() or self.take_profit_switch:

				self.execution_logic = 'TAKE PROFIT'

				self.on_event('profit', margin = 2)

				self.take_profit_switch = True

			elif self.is_hard_stop() or self.hard_stop_switch:

				self.execution_logic = 'HARD STOP'

				self.on_event('loss', margin = 0)

				self.hard_stop_switch = True

			elif self.is_soft_stop() or self.soft_stop_switch:

				self.execution_logic = 'SOFT STOP'

				self.on_event('loss', margin = 0)

				self.soft_stop_switch = True

		elif self.status == 'PENDING':
			
			if self.is_no_fill():

				self.execution_logic = 'NO FILL'

				self.on_close()

		elif self.status == 'CLOSING':
			pass

	## Action logic
	def is_candle_close(self):

		dt = datetime.now()
		return dt.minute % self.time_period == 0 and dt.second <= 1

	def is_in_profit(self):

		target = self.details['entry_price']
		return self.direction * (self.last_update - target) >= 0

	def is_take_profit(self):
		
		target = self.details['take_profit']
		return self.direction * (self.last_update - target) > 0 and self.is_candle_close()

	def is_hard_stop(self):

		target = self.details['hard_stop']
		return self.direction * (target - self.last_update) > 0

	def is_soft_stop(self):

		dt = datetime.now()
		target = self.details['soft_stop']
		return self.direction * (target - self.last_update) > 0 and self.is_candle_close()

	def is_matured(self):

		dt = datetime.now()
		delta = dt - self.init_time
		return delta.seconds >= self.time_period * self.maturity * 60

	def is_no_fill(self):

		dt = datetime.now()
		delta = dt - self.init_time
		return self.num_filled == 0 and delta.seconds >= self.time_period * 60
