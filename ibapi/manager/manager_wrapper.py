from ibapi.wrapper import EWrapper
from tools.zlogging import loggers

import numpy as np

import sys, os
import queue
from queue import Queue, LifoQueue
from datetime import datetime

class ManagerWrapper(EWrapper):

	def error(self, id_, error_code, error_msg):
		msg = '{}~-~{}~-~{}'.format(id_, error_code, error_msg)
		loggers['error'].info(msg)

		## ERROR HANDLING

		## Duplicate OIDs. Resend the order & change ID
		if error_code == 103:

			loggers['error'].warning("Duplicate OID - Rerouting")
			order, trade = self.orders[id_], self.order2trade[id_]
			oid = self.get_oid()
			trade.orders[order.key]['order_id'] = oid
			trade.update_and_send(order.key, order.lmtPrice)

	def nextValidId(self, orderId):
		self.order_id = orderId

	def orderStatus(self, orderId, status, filled, remaining, avgFilledPrice, 
					permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):

		try:

			print('o2t', self.order2trade.keys())
			## Get the trade object this order is concerning
			trade = self.order2trade[orderId]

			## Get the order itself
			print('orders', self.orders.keys())
			order = self.orders[orderId]

			if order.purpose == 'initiate':

				## Store the position filled
				trade.num_filled = filled

				## Store the average cost of the position
				trade.avg_filled_price = avgFilledPrice

				if status == 'Filled':
					loggers[trade.symbol].info('INIT TRADE:{}~-~{}'.format(filled, avgFilledPrice))
					trade.on_fill()

			elif order.purpose == 'close':

				## Store position filled on close
				trade.num_filled_on_close = filled

				## Store avg cost
				trade.avg_filled_price_on_close = avgFilledPrice

				if status == 'Filled':
					loggers[trade.symbol].info('CLOSED TRADE:{}~-~{}'.format(filled, avgFilledPrice))
					## Close the trade
					trade.on_close()

		except Exception as e:
			print('Im here - Order Status: {}'.format(status))
			print(e)

	def tickPrice(self, tickerId, field, price, attribs):

		try:

			trade = self.trades[self.id2ticker[tickerId]]
			if field == self.tick_types[trade.direction]:
				trade.last_update = price
				trade.on_period()

		except Exception as e:
			
			print(e)
