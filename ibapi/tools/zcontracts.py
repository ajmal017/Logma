from ibapi.contract import Contract

def forex_contract(first_ticker, second_ticker):

	contract = Contract()
	contract.symbol = first_ticker
	contract.secType = "CASH"
	contract.currency = second_ticker
	contract.exchange = "IDEALPRO"

	return contract

def canadian_stock(stock_ticker):

	contract = Contract()
	contract.symbol = stock_ticker
	contract.secType = "STK"
	contract.currency = "CAD"
	contract.exchange = "SMART"
	contract.primaryExchange = "TSE"

	return contract