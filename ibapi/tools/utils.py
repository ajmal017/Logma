import numpy as np

def adjust_price(price, tick_incr, direction, margin = 1, base = 5):

		## Add a 1 tick buffer
		price += ((tick_incr * margin) / base) * direction
		
		## Round the price
		price = 0.1 + price / (tick_incr / base) * direction
		price = base * np.floor(price/base) * direction

		return price / (base / tick_incr)