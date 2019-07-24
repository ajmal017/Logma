from ibapi.client import EClient

class HistoricalClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def request_historical(self):

		self.reqHistoricalData(*self.next_config())