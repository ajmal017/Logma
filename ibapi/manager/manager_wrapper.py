from ibapi.wrapper import EWrapper
from tools.zlogging import loggers

import numpy as np

import sys, os, time
from datetime import datetime

class ManagerWrapper(EWrapper):

	def error(self, id_, error_code, error_msg):

		## Keep track of health
		if error_code in [2103, 2104, 2108]:
			self.last_data_code = error_code

		msg = '{}~-~{}~-~{}'.format(id_, error_code, error_msg)
		loggers['error'].info(msg)

		## ERROR HANDLING
		## Duplicate OIDs. Resend the order & change ID
		if error_code == 103:

			loggers['error'].warning("Duplicate OID - Rerouting")
			
			order, trade = self.orders[id_], self.order2trade[id_]
			trade.orders[order.key]['order_id'] = self.get_oid()
			trade.update_and_send(order.key, order.lmtPrice)

			## Book keeping
			del self.order2trade[id_]
			del self.orders[id_]

		elif (error_code == 1100 or error_code == 2103) and self.state == "ALIVE":

			loggers['error'].warning("Manager Connection Lost - Waiting for reconnection message")

			self.state = "DEAD"

			for ticker in self.trades:

				self.cancelMktData(self.ticker2id[ticker])
				self.instruments[ticker].blocker.pause_job("manager_job")

		elif (error_code == 1102 or error_code == 1102 or error_code == 2104) and self.state == "DEAD":

			loggers['error'].warning("Manager Connection Regained - Waiting for initialization ")

			self.state = "ALIVE"
			self.disconnect()

			time.sleep(1)

			self.connect(*self.connection)

			for ticker in self.trades:

				self.reqMktData(self.ticker2id[ticker], self.contracts[ticker], '', False, False, [])
				self.instruments[ticker].blocker.resume_job("manager_job")

	def nextValidId(self, orderId):
		
		self.order_id = orderId

	def orderStatus(self, orderId, status, filled, remaining, avgFilledPrice, 
					permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):

		try:

			print('o2t', self.order2trade.keys())
			## Get the trade object this order is concerning
			trade = self.order2trade[orderId]

			## Get the order itself
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
			pass

	def tickPrice(self, tickerId, field, price, attribs):

		## To avoid concurrent deletion of trade + receiving mkt data
		try:

			trade = self.trades[self.id2ticker[tickerId]]
			if field == self.tick_types[trade.direction]:
				trade.last_update = price
				trade.on_period()

		except Exception as e:
			pass
