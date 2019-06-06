from datetime import datetime
from tools.zorders import limit_order, limit_if_touched
from tools.utils import adjust_price
from tools.zlogging import loggers, post_doc

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
		self.data = data

		## Manager stuff
		self.manager = manager
		self.tick_incr = manager.tick_increments[self.symbol]

		## Closing instructions
		self.details = details

		## Trade status
		self.status = 'PENDING'
		self.state = 'NORMAL'
		self.execution_logic = 'TAKE PROFIT'

		## Initial order quantity
		self.quantity = quantity

		## Place initial order
		self.setup()

		## Switches
		self.soft_stop_switch = True
		self.take_profit_switch = True
		self.hard_stop_switch = True

		## Placeholders
		self.num_filled = 0
		self.num_filled_on_close = 0
		self.drawdown = 0
		self.run_up = 0
		self.avg_filled_price_on_close = -1
		self.avg_filled_price = -1
		self.execution_time = -1

		## Period details
		self.time_period = 1
		self.maturity = 20

		self.logger = loggers[symbol]

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

			## Send closing orders
			profit_oid = self.manager.get_oid()
			self.manager.placeOrder(profit_oid, self.contract, self.orders['profit']['order'])

			## Book keeping
			self.orders['profit']['order_id'] = profit_oid
			self.manager.orders[profit_oid] = self.orders['profit']['order']
			self.manager.order2trade[profit_oid] = self

			print('Profit', self.symbol, profit_oid)

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
			#post_doc(self)

			self.status == 'CLOSED'

	def update_and_send(self, order_key, adjusted_price):

		self.orders[order_key]['order'].lmtPrice = adjusted_price
		#self.orders[order_key]['order'].totalQuantity = self.quantity - self.num_filled_on_close

		oid = self.orders[order_key]['order_id']
		oid = oid if oid is not None else self.manager.get_oid()
		self.manager.placeOrder(oid, self.contract, self.orders[order_key]['order'])
		print(order_key, self.symbol, oid)

		## Book keeping
		self.orders[order_key]['order_id'] = oid
		self.manager.orders[oid] = self.orders[order_key]['order']
		self.manager.order2trade[oid] = self

	def on_period(self):
		
		if self.status == 'ACTIVE':

			## Calculate drawdown/runup
			self.drawdown = min(self.direction * (self.last_update - self.avg_filled_price), self.drawdown)
			self.run_up = max(self.direction * (self.last_update - self.avg_filled_price), self.run_up)

			if self.is_hard_stop() and self.hard_stop_switch:

				self.execution_logic = 'HARD STOP'

				adjusted_price = adjust_price(self.last_update, self.tick_incr, self.direction, margin = 1)
				if self.orders['loss']['order'].lmtPrice != adjusted_price:
					self.update_and_send('loss', adjusted_price)

			elif self.is_soft_stop() and self.soft_stop_switch: 

				self.execution_logic = 'SOFT STOP'

				adjusted_price = adjust_price(self.last_update, self.tick_incr, self.direction, margin = 1)
				if self.orders['loss']['order'].lmtPrice != adjusted_price:
					self.update_and_send('loss', adjusted_price)

			elif self.is_matured():

				self.logger.info('MATURITY State reached.')
				self.state = 'MATURITY'

				factor = 1 if self.is_in_profit() else -1
				self.details['hard_stop'] = adjust_price(self.last_update, self.tick_incr, factor * self.direction, margin = 1)
				self.soft_stop_switch = False

		elif self.status == 'PENDING':
			
			if self.is_no_fill():

				self.execution_logic = 'NO FILL'

				self.on_close()

		elif self.status == 'CLOSING':
			pass

	## Action logic
	def is_in_profit(self):

		target = self.details['entry_price']
		return self.direction * (self.last_update - target) >= 0

	def is_take_profit(self):
		
		target = self.details['take_profit']
		return self.direction * (self.last_update - target) > 0

	def is_hard_stop(self):

		target = self.details['hard_stop']
		return self.direction * (target - self.last_update) > 0

	def is_soft_stop(self):

		dt = datetime.now()
		target = self.details['soft_stop']
		return dt.minute % 1 == 0 and dt.second == 0 and self.direction * (target - self.last_update) > 0

	def is_matured(self):

		dt = datetime.now()
		delta = dt - self.init_time
		return delta.seconds >= self.time_period * self.maturity * 60

	def is_no_fill(self):

		dt = datetime.now()
		delta = dt - self.init_time
		return self.num_filled == 0 and delta.seconds >= self.time_period * 60
