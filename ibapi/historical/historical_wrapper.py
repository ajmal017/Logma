from ibapi.wrapper import EWrapper
from datetime import datetime, timedelta
import time
import pandas as pd

class HistoricalWrapper(EWrapper):

	def error(self, reqId, error_code, error_msg):

		print(reqId, error_code, error_msg)

		if error_code == 162:
			df = pd.DataFrame(self.data[::-1], columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
			df['Datetime'] = pd.to_datetime(df.Datetime.values, format='%Y%m%d  %H:%M:%S')
			df = df.sort_values('Datetime', ascending=True)
			df.to_csv('D:/AlgoMLData/IBData/%s' % self.ticker, index=False)
			self.disconnect()
			1/0

	def historicalData(self, reqId, bar):
		
		self.data.append((bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume))

	def historicalDataEnd(self, reqId, start, end):
		
		self.period += 1
		self.cdt = datetime.strptime(start, '%Y%m%d  %H:%M:00')
		self.data_lens.append(len(self.data))
		self.data_lens = self.data_lens[-5:]
		print(self.cdt, len(self.data), start, end)

		self.request_historical()