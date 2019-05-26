from apscheduler.schedulers.background import BackgroundScheduler
from viz_wrapper import VizWrapper
from viz_client import VizClient
from dash_thread import DashThread
from dash.dependencies import Input, Output

import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import dash_table

from threading import Thread
from multiprocessing import Process
from datetime import datetime
from querying import *

import plotly.figure_factory as ff

import dash
import pandas as pd
import numpy as np
import signal
import sys, os

class Viz(VizClient, VizWrapper):

	def __init__(self, ip_address, port):

		VizWrapper.__init__(self)
		VizClient.__init__(self, self)

		## Start all connections
		self.connect(ip_address, port, 3)

		thread = Thread(target = self.run)
		thread.start()

		## Placeholders
		self.positions = []
		self.states = ["ACTIVE", "PENDNG"]
		self.status = ["NORMAL", "MATURE"]
		self.execution_logics = ["NO FILL", "TAKE PROFIT", "SOFT STOP", "HARD STOP"]
		self.directions = ["BUY", "SELL"]
		self.tickers = ["EURCHF","USDCHF","GBPUSD","USDJPY","EURUSD","EURGBP","NZDUSD","USDCAD","EURJPY","AUDUSD","GBPJPY","CHFJPY","AUDNZD","CADJPY"]
		self.reset_filter = [
			time_query(None, None),
			terms_query("ticker", self.tickers),
			terms_query("action", self.directions),
			terms_query("state", self.states),
			terms_query("status", self.status),
			terms_query("executionLogic", self.execution_logics),
		]

		## Input List
		self.filter_inputs = [Input("historical_dates", "start_date"),
								Input("historical_dates", "end_date"),
								Input("historical_tickers", "value"),
								Input("historical_directions", "value"),
								Input("historical_states", "value"),
								Input("historical_status", "value"),
								Input("historical_execution_logic", "value"),
								Input("historical_reset", "value")]

		## Static DFs for initial homepage
		self.live_positions_columns = ['Ticker', 'Direction', 'Position', 'Price', 'MktValue', 'AvgCost', 'LivePNL']
		self.live_positions_df = pd.DataFrame([], columns = self.live_positions_columns)

		## Initialize historical data
		self.historical_positions_columns = ["Ticker", "Action", "Status", "ExecutionLogic", "State", "Drawdown", "runUp", "% Profit"]
		self.init_historicals([])

		## Initialize Dash App
		self.app = dash.Dash()
		self.init_layout()

		## Initialize the thread
		self.app_thread = DashThread(self.app)
		self.app_thread.start()

		self.bg_scheduler = BackgroundScheduler()
		self.bg_scheduler.add_job(self.get_account_updates,"cron", second="*/15")
		self.bg_scheduler.start()

	def init_historicals(self, filters):

		results = es.search(index="retracements", body = query(filters))

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
				self.drawdown_dist.append(trade['_source']['drawdown'] * -1) 
				self.return_dist.append((trade['_source']['direction'] * (trade['_source']['avgCostOnClosed'] - trade['_source']['avgCost'])) / trade['_source']['avgCost'])
				
			else:
				
				data.extend([
					"N/A", 0, 0, 0
				])
			
			stats.append(data)

		self.historical_positions_df = pd.DataFrame(stats, columns = self.historical_positions_columns)

		keys = ['NO FILL', 'TAKE PROFIT', 'SOFT STOP', 'HARD STOP']
		self.executions = self.historical_positions_df.ExecutionLogic.value_counts().to_dict()
		for key in keys:
			if key not in self.executions:
				self.executions[key] = 0

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

	def get_filters(self, start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

		if reset == "ALL":
			return []
		else:
			return [
				time_query(start_date, end_date),
				terms_query("ticker", tickers),
				terms_query("action", directions),
				terms_query("state", states),
				terms_query("status", statuses),
				terms_query("executionLogic", execution_logic)
			]

	def header(self):

		return html.H1(
				id = "main_header",
				children = "zQP - Retracement", 
				style = {
					"textAlign" : "left",
					"color" : "black"
				}
			)

	def init_layout(self):

		self.app.layout = html.Div([
				self.header(),
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
						   self.filter_inputs)
		def update_historical_graph(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = []
			filters.append(time_query(start_date, end_date))
			filters.append(terms_query("ticker", tickers))
			filters.append(terms_query("action", directions))
			filters.append(terms_query("state", states))
			filters.append(terms_query("status", statuses))
			filters.append(terms_query("executionLogic", execution_logic))
			filters = [] if reset == "ALL" else filters

			self.init_historicals(filters)

			fig = ff.create_distplot([self.drawdown_dist, self.run_up_dist], ['dradowns', 'runUps'])

			return fig

		@self.app.callback(Output("historical_positions_returns", "figure"),
						   self.filter_inputs)
		def update_historical_graph(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			fig = ff.create_distplot([self.return_dist], ['returns'])

			return fig

		@self.app.callback(Output("historical_tickers", "options"),
						   self.filter_inputs)
		def update_historical_ticker_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			return self.ticker_labels

		@self.app.callback(Output("historical_execution_logic", "options"),
						   self.filter_inputs)
		def update_historical_execution_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			return self.execution_logic_labels

		@self.app.callback(Output("historical_states", "options"),
						   self.filter_inputs)
		def update_historical_state_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			return self.state_labels

		@self.app.callback(Output("historical_status", "options"),
						   self.filter_inputs)
		def update_historical_status_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			return self.status_labels

		@self.app.callback(Output("historical_directions", "options"),
						   self.filter_inputs)
		def update_historical_direction_labels(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			return self.direction_labels

		@self.app.callback(Output("historical_positions_table", "data"),
						   self.filter_inputs)
		def update_historical_table(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			return self.historical_positions_df.to_dict('rounded')

		@self.app.callback(Output("historical_positions_nofills", "figure"),
						   self.filter_inputs)
		def update_historical_table(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			labels = ['No Fills', 'Filled Trades']
			values = [self.executions['NO FILL'], sum(list(self.executions.values())) - self.executions['NO FILL']]

			return {
						"data" : [
							{
								"values" : values,
								"type" : "pie",
								"labels" : labels
							}
						]
					}

		@self.app.callback(Output("historical_positions_success", "figure"),
						   self.filter_inputs)
		def update_historical_table(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset):

			filters = self.get_filters(start_date, end_date, tickers, directions, states, statuses, execution_logic, reset)

			self.init_historicals(filters)

			labels = ['Success', 'Failure']
			values = [self.executions['TAKE PROFIT'], sum(list(self.executions.values())) - self.executions['TAKE PROFIT'] - self.executions['NO FILL']]

			return {
						"data" : [
							{
								"values" : values,
								"type" : "pie",
								"labels" : labels
							}
						]
					}

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
					html.Br(),
					html.Br(),
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
						interval = 5 * 1000,
						n_intervals = 0
					)
				],
				style = {
						"width" : "48.5%",
						"display" : "inline-block",
						"verticalAlign" : "top",
						"marginRight" : "1.5%"
					}
				)

	def historical_positions(self):

		fig = ff.create_distplot([self.drawdown_dist, self.run_up_dist], ['dradowns', 'runUps'])
		fig2 = ff.create_distplot([self.return_dist], ['returns'])

		labels = ['No Fills', 'Filled Trades']
		values = [self.executions['NO FILL'], sum(list(self.executions.values())) - self.executions['NO FILL']]

		labels2 = ['Success', 'Failure']
		values2 = [self.executions['TAKE PROFIT'], sum(list(self.executions.values())) - self.executions['TAKE PROFIT'] - self.executions['NO FILL']]

		return html.Div([
				dcc.DatePickerRange(
						id = "historical_dates",
						start_date_placeholder_text = "Starting date",
						end_date_placeholder_text = "Ending date",
				),
				html.Br(),
				dcc.Dropdown(
						id = "historical_tickers",
						options = self.ticker_labels,
						value=[dict_["value"] for dict_ in self.ticker_labels],
						multi=True
					),
				dcc.Dropdown(
						id = "historical_states",
						options = self.state_labels,
						value=[dict_["value"] for dict_ in self.state_labels],
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_execution_logic",
						options = self.execution_logic_labels,
						value=[dict_["value"] for dict_ in self.execution_logic_labels],
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_directions",
						options = self.direction_labels,
						value=[dict_["value"] for dict_ in self.direction_labels],
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_status",
						options = self.status_labels,
						value=[dict_["value"] for dict_ in self.status_labels],
						multi=True 
					),
				dcc.Dropdown(
						id = "historical_reset",
						options = [
							{"value" : "ALL", "label" : "ALL"},
							{"value" : "FILTER", "label" : "FILTER"}
						],
						value = ["FILTER", "ALL"],
						multi = False
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
				dcc.Graph(
					id = "historical_positions_distplot",
					figure = fig
				),
				dcc.Graph(
						id = "historical_positions_returns",
						figure = fig2
					),
				html.Div([
					dcc.Graph(
							id = "historical_positions_nofills",
							figure = {
								"data" : [
									{
										"values" : values,
										"type" : "pie",
										"labels" : labels
									}
								]
							},
							style = {
								"width" : "48%",
								"display" : "inline-block"
							}
						),
					dcc.Graph(
							id = "historical_positions_success",
							figure = {
								"data" : [
									{
										"values" : values2,
										"type" : "pie",
										"labels" : labels2
									}
								]
							},
							style = {
								"width" : "48%",
								"display" : "inline-block"
							}
						)
					],
					style = {
						"display" : "inline-block"
					})
				
			],
			style = {
				"width" : "48.5%",
				"align" : "right",
				"display" : "inline-block",
				"marginLeft" : "1.5%"
			})

	def on_close(self):

		self.bg_scheduler.shutdown()
		self.disconnect()
		self.app_thread.raise_exception()
		self.app_thread.join()

if __name__ == '__main__':

	viz = Viz('127.0.0.1', 4001)

