from ibapi.wrapper import EWrapper
import pandas as pd

class VizWrapper(EWrapper):

	def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):

		self.positions.append([
				contract.symbol + contract.currency,
				"LONG",
				position,
				marketPrice,
				marketValue,
				averageCost,
				unrealizedPNL
			])

	def accountDownloadEnd(self, account):

		self.live_positions_df = pd.DataFrame(self.positions, columns = self.live_positions_columns)