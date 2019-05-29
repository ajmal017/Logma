from ibapi.order import Order

def default_order(action, quantity, purpose, key):

	order = Order()
	order.action = action
	order.totalQuantity = quantity
	order.purpose = purpose
	order.key = key
	return order

def market_order(action, quantity, price, purpose, key):

	order = default_order(action, quantity, purpose, key)
	order.orderType = 'MKT'
	return order

def limit_order(action, quantity, price, purpose, key):

	order = default_order(action, quantity, purpose, key)
	order.orderType = "LMT"
	order.lmtPrice = price
	return order

def market_if_touched(action, quantity, price, purpose, key):

	order = default_order(action, quantity, purpose, key)
	order.orderType = "MIT"
	order.auxPrice = price

	return order

def limit_if_touched(action, quantity, limit_price, trigger_price, purpose, key):

	order = default_order(action, quantity, purpose, key)
	order.orderType = "LIT"
	order.lmtPrice = limit_price
	order.auxPrice = trigger_price

	return order