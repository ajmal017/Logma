from viz_wrapper import VizWrapper
from viz_client import VizClient
from viz_components import *
from dash_thread import DashThread

from dash.dependencies import Input, Output

import plotly.figure_factory as ff

import dash
import pandas as pd
import numpy as np
import signal
import sys, os

from threading import Thread
from multiprocessing import Process
from datetime import datetime

from querying import *

class Viz(VizClient, VizWrapper):

	def __init__(self, ip_address, port):

		VizWrapper.__init__(self)
		VizClient.__init__(self, self)

		## Placeholders
		self.positions = []

		## Static DFs for initial homepage
		self.live_positions_columns = ['Ticker', 'Direction', 'Position', 'Price', 'MktValue', 'AvgCost', 'LivePNL']
		self.live_positions_df = pd.DataFrame([], columns = self.live_positions_columns)

		## Initialize historical data
		self.historical_positions_columns = ["Ticker", "Action", "Status", "ExecutionLogic", "State", "Drawdown", "runUp", "% Profit"]
		self.init_historicals()

		## Initialize Dash App
		self.app = dash.Dash()
		self.init_layout()

		## Initialize the thread
		self.app_thread = DashThread(self.app)
		self.app_thread.start()

		## Start all connections
		self.connect(ip_address, port, 3)
		thread = Thread(target = self.run)
		thread.start()

	def init_historicals(self, *args):

		results = es.search(index="retracements", body = query(*args))

		stats = []
		self.run_up_dist = []
		self.drawdown_dist = []
		self.return_dist = []

		for trade in results['hits']['hits']:

			data = [
				trade['_source']['ticker'],
				trade['_source']['action'],
				trade['_source']['status'],
				trade['_source']['executionLogic'],
			]
			
			if 'drawdown' in trade['_source']:
				
				data.extend([
					trade['_source']['state'],
					trade['_source']['drawdown'],
					trade['_source']['runUp'],
					(trade['_source']['direction'] * (trade['_source']['avgCostOnClosed'] - trade['_source']['avgCost'])) / trade['_source']['avgCost']
				])
				
				self.run_up_dist.append(trade['_source']['runUp'])
				self.drawdown_dist.append(trade['_source']['drawdown'])
				self.return_dist.append((trade['_source']['direction'] * (trade['_source']['avgCostOnClosed'] - trade['_source']['avgCost'])) / trade['_source']['avgCost'])
				
			else:
				
				data.extend([
					"N/A", 0, 0, 0
				])
			
			stats.append(data)

		self.historical_positions_df = pd.DataFrame(stats, columns = self.historical_positions_columns)

		## State
		self.state_labels = []
		for bucket in results['aggregations']['stateAggs']['buckets']:
		    self.state_labels.append({"label" : "{} ({})".format(bucket['key'], bucket['doc_count']), "value" : bucket['key']})

		## Direction
		self.direction_labels = []
		for bucket in results['aggregations']['directionAggs']['buckets']:
		    self.direction_labels.append({"label" : "{} ({})".format(bucket['key'], bucket['doc_count']), "value" : bucket['key']})
		    
		## executionLogic
		self.execution_logic_labels = []
		for bucket in results['aggregations']['executionLogicAggs']['buckets']:
		    self.execution_logic_labels.append({"label" : "{} ({})".format(bucket['key'], bucket['doc_count']), "value" : bucket['key']})
		    
		## ticker aggs
		self.ticker_labels = []
		for bucket in results['aggregations']['tickerAggs']['buckets']:
		    self.ticker_labels.append({"label" : "{} ({})".format(bucket['key'], bucket['doc_count']), "value" : bucket['key']})    

		## State
		self.status_labels = []
		for bucket in results['aggregations']['statusAggs']['buckets']:
		    self.status_labels.append({"label" : "{} ({})".format(bucket['key'], bucket['doc_count']), "value" : bucket['key']})

	def init_layout(self):

		self.app.layout = html.Div([
				app_header(),
				self.live_positions(),
				self.historical_positions()
			])

		## Callbacks
		@self.app.callback(Output("live_positions_table", "data"),
						  [Input("live_positions_interval", "n_intervals")])
		def update_table(n):
			return self.live_positions_df.to_dict('rounded')

		@self.app.callback(Output("live_positions_graph", "figure"),
						   [Input("live_positions_interval", "n_intervals")])
		def update_graph(n):

			tickers = self.live_positions_df.Ticker.tolist() + ["Net"]
			pnl = self.live_positions_df.LivePNL.tolist()
			pnl += [sum(pnl)]

			return {
					"data" : [
						{"x" : tickers,
						 "y" : pnl,
						"type" :  "bar",
						"name" : "live positions",
						"marker" : dict(color=["green" if p >= 0 else "red" for p in pnl])}
					],
					"layout" : go.Layout(
							title = "Live Positions",
							xaxis = {"title" : "Tickers"},
							yaxis = {"title" : "Profit & Loss"}
						)
				}

		@self.app.callback(Output("historical_positions_distplot", "figure"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_graph(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			fig = ff.create_distplot([self.drawdown_dist, self.run_up_dist], ['dradowns', 'runUps'])

			return fig

		@self.app.callback(Output("historical_tickers", "options"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_ticker_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			return self.ticker_labels

		@self.app.callback(Output("historical_execution_logic", "options"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_execution_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			return self.execution_logic_labels

		@self.app.callback(Output("historical_states", "options"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_state_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			return self.state_labels

		@self.app.callback(Output("historical_status", "options"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_status_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			return self.status_labels

		@self.app.callback(Output("historical_directions", "options"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_direction_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			return self.direction_labels

		@self.app.callback(Output("historical_positions_table", "data"),
						   [Input("historical_dates", "start_date"),
						    Input("historical_dates", "end_date"),
						    Input("historical_tickers", "value"),
						    Input("historical_directions", "value"),
						    Input("historical_states", "value"),
						    Input("historical_status", "value"),
						    Input("historical_execution_logic", "value")])
		def update_historical_table(start_date, end_date, tickers, directions, states, statuses, execution_logic):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))

			self.init_historicals(*filters)

			return self.historical_positions_df.to_dict('rounded')


	def live_positions(self):

		tickers = self.live_positions_df.Ticker.tolist() + ["Net"]
		pnl = self.live_positions_df.LivePNL.tolist()
		pnl += [sum(pnl)]

		return html.Div([
					dcc.Graph(
						id = "live_positions_graph",
						figure = {
							"data" : [
								{"x" : tickers,
								 "y" : pnl,
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
						id = "live_positions_table",
						columns = [{'id' : col, 'name' : col} for col in self.live_positions_df.columns],
						data = self.live_positions_df.to_dict('rounded'),
						style_table = {
							"width" : "100%",
							"align" : "left"
						}
					),
					dcc.Interval(
						id = "live_positions_interval",
						interval = 60 * 1000,
						n_intervals = 0
					)
				],
				style = {
						"width" : "50%",
						"display" : "inline-block"
					}
				)

	def historical_positions(self):

		fig = ff.create_distplot([self.drawdown_dist, self.run_up_dist], ['dradowns', 'runUps'])

		return html.Div([
				dcc.Graph(
					id = "historical_positions_distplot",
					figure = fig
				),
				dash_table.DataTable(
						id = "historical_positions_table",
						columns = [{'id' : col, 'name' : col} for col in self.historical_positions_columns],
						data = self.historical_positions_df.to_dict('rounded'),
						style_table = {
							"width" : "100%",
							"align" : "right",
							"overflowY" : "scroll",
							"height" : 200
						}
				),
				dcc.DatePickerRange(
					id = "historical_dates",
					start_date = datetime.now().strftime('%Y-%m-%d'),
					end_date = datetime.now().strftime('%Y-%m-%d'),
					start_date_placeholder_text = "Starting date",
					end_date_placeholder_text = "Ending date",
				),
				html.Br(),
				dcc.Dropdown(
						id = "historical_tickers",
						options = self.ticker_labels,
						value=[dict_["value"] for dict_ in self.ticker_labels],
						disabled=False,
						multi=True
					),
				dcc.Dropdown(
						id = "historical_states",
						options = self.state_labels,
						value=[dict_["value"] for dict_ in self.state_labels],
						disabled=False,
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_execution_logic",
						options = self.execution_logic_labels,
						value=[dict_["value"] for dict_ in self.execution_logic_labels],
						disabled=False,
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_directions",
						options = self.direction_labels,
						value=[dict_["value"] for dict_ in self.direction_labels],
						disabled=False,
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_status",
						options = self.status_labels,
						value=[dict_["value"] for dict_ in self.status_labels],
						disabled=False,
						multi=True 
					)
				
			],
			style = {
				"width" : "50%",
				"align" : "right",
				"display" : "inline-block"
			})

	def on_close(self):

		self.disconnect()
		self.app_thread.raise_exception() 
		self.app_thread.join()

if __name__ == '__main__':

	viz = Viz('127.0.0.1', 4001)

