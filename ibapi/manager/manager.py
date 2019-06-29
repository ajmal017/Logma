from apscheduler.schedulers.background import BackgroundScheduler

from manager.manager_client import ManagerClient
from manager.manager_wrapper import ManagerWrapper

from threading import Thread
from datetime import datetime

from trade import Trade
from tools.zcontracts import forex_contract

import logging

##############################

#ip_address = '192.168.2.26'
ip_address = '127.0.0.1'
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

		## OID Offset
		self.order_id_offset = 0

		## OrderID 2 trade
		self.order2trade = {}

		## Trade object storage
		self.trades = {}

		## OrderId to Order mapping
		self.orders = {}

		## Connection Details
		self.connection = (ip_address, port, clientId)

		## State
		self.state = "ALIVE"

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

		## Max risk
		self.risk = 2.5

		## Data health
		self.last_error_code = 2104

		## Connect to gateway
		self.connect(*self.connection)

		## Init message loop
		thread = Thread(target = self.run)
		thread.start()

	def get_oid(self):

		self.order_id += 1
		return self.order_id

	def on_start(self):

		for ticker in os.listdir('db/trades/'):

			self.loggers['error'].info('De-serialize {} Trade.'.format(ticker))

			with open('db/trades/{}'.format(ticker)) as file:

				serialized_trade = joblib.load(file)
				assert serialized_trade['symbol'] == ticker

				self.trades[ticker] = Trade(self, symbol = None, **kwargs)

				self.reqMktData(self.ticker2id[ticker], self.contracts[ticker], '', False, False, [])


	def now(self):

		return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	def on_close(self):

		for ticker in self.trades:

			## Dont save trades that are not even filled.
			if self.trades[ticker].status == 'PENDING':
				continue
			
			self.trades[ticker].serialize()

		## Close all orders
		self.reqGlobalCancel()

		## Disconnect ClientID
		self.disconnect()

if __name__ == '__main__':

	manager = Manager(ip_address, port)

