import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objs as go

def app_header():

	return html.H1(children = "zQP - Retracement",
				id = "main_header",
				style = {
					"textAlign" : "left",
					"color" : "red"
				}
			)

def live_positions():

	return html.Div([
				dcc.Graph(
					id = "live positions graph",
					figure = {
						"data" : [
							{"x" : ["EURUSD", "USDCAD", "EURCHF"],
							 "y" : [10, -7, 20],
							"type" :  "bar",
							"name" : "live positions"}
						],
						"layout" : go.Layout(
								title = "Live Positions",
								xaxis = {"title" : "Tickers"},
								yaxis = {"title" : "Profit & Loss"}
							)
					},
					style = {
						"width" : "100%",
						"align" : "left"
					}
				),
				dash_table.DataTable(
					id = "live positions table",
					columns = [{"name" : "ticker", "id" : "ticker"}, {"name" : "profit", "id" : "profit"}],
					data = [{"ticker" : "EURUSD", "profit" : 100}, {"ticker" : "USDJPY", "profit" : -100}],
					style_table = {
						"width" : "100%",
						"align" : "left"
					}
				),
			],
			style = {
				"width" : "50%"
				}
			)

def dropdown():

	return dcc.Dropdown(
				id = "ticker_selection",
				options = [
					{"label" : "EURCHF", "value" : "EURCHF"},
					{"label" : "USDCHF", "value" : "USDCHF"},
					{"label" : "GBPUSD", "value" : "GBPUSD"},
					{"label" : "USDJPY", "value" : "USDJPY"},
					{"label" : "EURUSD", "value" : "EURUSD"},
					{"label" : "EURGBP", "value" : "EURGBP"},
					{"label" : "NZDUSD", "value" : "NZDUSD"},
					{"label" : "USDCAD", "value" : "USDCAD"},
					{"label" : "EURJPY", "value" : "EURJPY"},
					{"label" : "AUDUSD", "value" : "AUDUSD"},
					{"label" : "GBPJPY", "value" : "GBPJPY"},
					{"label" : "CHFJPY", "value" : "CHFJPY"},
					{"label" : "AUDNZD", "value" : "AUDNZD"},
					{"label" : "CADJPY", "value" : "CADJPY"}
				],
				placeholder = "Choose a ticker"
			)