from ibapi.client import EClient


class VizClient(EClient):

	def __init__(self, wrapper):

		EClient.__init__(self, wrapper = wrapper)

	def get_account_updates(self):

		self.reqAccountUpdates(True, "")