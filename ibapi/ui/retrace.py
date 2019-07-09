from flask import Flask, render_template
from gevent.pywsgi import WSGIServer

from strategy_thread import StrategyThread

import atexit
from apscheduler.schedulers.background import BackgroundScheduler

from copy import deepcopy
import time
import pandas as pd

###########################################################
### Static Variables
###########################################################

cols = ["Ticker", "Direction", "Status", "State", "Last Update", "Candle Size", 
		"Avg Filled Price", "Take Profit Price", "Soft Stop Price", "Initiated Time", 
		"Execution Time", "Execution Logic", "Drawdown", "Run Up", "Trade Length", 
		"Quantity", "Filled Position"]

app = Flask(__name__)

###########################################################
### UI Events
###########################################################
def get_table():

	if len(strat.strategy.manager.trades) == 0:
		return pd.DataFrame(columns=cols).to_html()

	start = time.time()
	trades = []

	for ticker in strat.strategy.manager.trades:
		trades.append(strat.strategy.manager.trades[ticker].simple_view())

	df = pd.DataFrame(trades)
	df = df[cols]
	df.sort_values('Status', inplace=True)

	return df.to_html(classes=["table", "table-hover", "thead-dark"])

def get_health():

	colors = ["#14ba14", "#ede91a", "#ef1010"]

	## 2103, 2104, 2108
	manager_data_code = strat.strategy.manager.last_data_code
	manager_color = min(manager_data_code - 2104, 1)
	manager_color = colors[manager_color]

	## 2105, 2106, 2107
	scanner_data_code = strat.strategy.scanner.last_data_code
	scanner_color = scanner_data_code - 2106
	scanner_color = colors[scanner_color]

	colors = [colors[-1], colors[0]]
	api_code = int(strat.strategy.manager.isConnected() & strat.strategy.scanner.isConnected())
	api_color = colors[api_code]

	return {
		"manager" : manager_color,
		"scanner" : scanner_color,
		"api" : api_color
	}

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/')
def dashboard():

	## Positions
	position_table = get_table()

	## System Health
	system_health = get_health()

	return render_template("index.html", position_table = position_table, system_health = system_health)

if __name__ == '__main__':

	try:
	
		strat = StrategyThread(num_periods = 50, short_num_periods = 20, time_period = 5)
		strat.start()

		http_server = WSGIServer(('0.0.0.0', 9095), app)
		http_server.serve_forever()

	except Exception as e:

		strat.on_close()
		strat.join()

	finally:

		strat.on_close()
		strat.join()
