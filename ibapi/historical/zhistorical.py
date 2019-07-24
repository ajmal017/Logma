from historical_client import HistoricalClient
from historical_wrapper import HistoricalWrapper
from ibapi.contract import Contract

from datetime import datetime, timedelta
from threading import Thread

def forex_contract(first_ticker, second_ticker):

	contract = Contract()
	contract.symbol = first_ticker
	contract.secType = "CASH"
	contract.currency = second_ticker
	contract.exchange = "IDEALPRO"

	return contract


class zHistorical(HistoricalClient, HistoricalWrapper):

	def __init__(self, t1, t2, i):

		HistoricalWrapper.__init__(self)
		HistoricalClient.__init__(self, self)

		self.data = []
		self.data_lens = []
		self.ticker = t1 + t2
		self.contract = forex_contract(t1, t2)

		self.period = 0
		self.cdt = datetime.now()
		self.fmt = '%Y%m%d %H:%M:00'

		self.connect('127.0.0.1', 4001, i)

		self.main_thread = Thread(target = self.run)
		self.main_thread.start()


	def next_config(self):

		return (
				self.period, 
				self.contract,
				(self.cdt - timedelta(weeks=1)).strftime(self.fmt),
				'1 W',
				'5 mins',
				'MIDPOINT',
				1,
				1,
				False,
				[]
			)


if __name__ == '__main__':

	try:
		h = zHistorical('USD', 'CAD')
		h.request_historical()
	except Exception as e:
		print(e)
		h.main_thread.join()
		h.disconnect()
	finally:
		h.main_thread.join()
		h.disconnect()
