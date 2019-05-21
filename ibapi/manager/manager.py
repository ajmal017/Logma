from apscheduler.schedulers.background import BackgroundScheduler

from manager.manager_client import ManagerClient
from manager.manager_wrapper import ManagerWrapper

from threading import Thread
from datetime import datetime

from zcontracts import forex_contract

import logging

##############################

ip_address = '192.168.2.26'
port = 4001
clientId = 1

##############################

class Manager(ManagerClient, ManagerWrapper):

	def __init__(self, ip_address, port, clientId, ticker2id, id2ticker, contracts, tick_increments):

		ManagerWrapper.__init__(self)
		ManagerClient.__init__(self, self)

		## Instrument configuration
		self.ticker2id = ticker2id
		self.id2ticker = id2ticker
		self.contracts = contracts
		self.tick_increments = tick_increments

		## Reserving OrderIDs
		self.order_id_offset = 0

		## OrderID 2 trade
		self.order2trade = {}

		## Trade object storage
		self.trades = {}

		## OrderId to Order mapping
		self.orders = {}

		## Direction integer mappings
		self.action2direction = {
			"BUY" : 1,
			"SELL" : -1
		}

		## Direction to action mapping
		self.direction2action = {
			1 : "BUY",
			-1 : "SELL"
		}

		## Direction tick types
		self.tick_types = {
			1 : 1,
			-1 : 2
		}

		## Inverse Orders
		self.closing_actions = {
			"BUY" : "SELL",
			"SELL" : "BUY"
		}

		## Connect to gateway
		self.connect(ip_address, port, clientId)

		## Init message loop
		thread = Thread(target = self.run)
		thread.start()

	def on_start(self):

		pass

	def now(self):

		return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	def on_close(self):

		## Close all orders
		self.reqGlobalCancel()

		## Disconnect ClientID
		self.disconnect()

if __name__ == '__main__':

	manager = Manager(ip_address, port)

