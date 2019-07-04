from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from elasticsearch import helpers
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import mpl_finance as mf
from es_setup import es
import pandas as pd
import smtplib, ssl
import numpy as np
import time, io
import sys, os

dir_ = 'dumps/'

def simple_ohlc(data, avgCost, takeProfit, stopLoss):

    data = data.copy()
    data[:, 0] = mdates.date2num(pd.to_datetime(data[:, 0]).values)
    data = data.astype(float)
    
    fig, ax = plt.subplots(figsize=(20, 9))
    plt.title('Strategy Execution')
    
    ## Plot the candles
    for row in data:
        _ = mf.candlestick_ohlc(ax, [row], width=0.0002)
    
    ## Display strategy
    plt.axhline(y=takeProfit, color='g')
    plt.axhline(y=stopLoss, color='r')
    plt.axhline(y=avgCost, xmin = (50-1) / len(data), color='black', linestyle='--')
    
    ## Encode the image for easy transferring
    img_ = None
    with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
    return img_

def plot_price_updates(updates):
    
    plt.figure(figsize=(20, 4))
    plt.title('Price Updates per Candle')
    plt.xlabel('Candle')
    plt.ylabel('Updates')
    plt.bar(np.arange(len(updates)), updates)
    
    ## Encode the image for easy transferring
    img_ = None
    with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
    return img_ 

def notify_(trade):

	####################################
	## TRADE DETAILS
	####################################
	# Summary
	ticker = trade['ticker']
	action = trade['action']
	quantity = int(trade.get('position', 0))
	avg_price = trade.get('avgCost', 'NaN')

	# Profitability
	risk = np.round((trade['candleSize'] * 2.5), 2)
	reward = np.round(trade['candleSize'], 2)
	if trade['executionLogic'] != 'NO FILL':
		runup = np.round((trade['runUp'] / trade['tickIncrement']) / reward, 2)
		drawdown = np.round((trade['drawdown'] / trade['tickIncrement']) / risk, 2)
		realized = np.round((trade['direction'] * (trade['avgCostOnClose'] - trade['avgCost'])) / trade['tickIncrement'], 2)
	else:
		runup, drawdown, realized = 0, 0, 0

	# Behaviour
	state = trade['state']
	status = trade['status']
	logic = trade['executionLogic']
	length = len(trade['numUpdates'])

	# Order details
	entry = trade['entryLimitPrice']
	profit = trade['takeProfitLimitPrice']
	stop = trade['stopLossLimitPrice']

	# Chronology
	init = trade['initTime']
	execution = trade.get('executionTime', 'NaN')
	closing = trade.get('closingTime', 'NaN')

	## Get the plots ready
	data = [[date]+list(prices) for date, prices in zip(trade['data']['preDates'], trade['data']['prePrices'])]
	data += [[date]+list(prices) for date, prices in zip(trade['data']['postDates'], trade['data']['postPrices'])]

	price_plot = simple_ohlc(data = np.array(data), avgCost = avg_price, takeProfit=profit, stopLoss = stop)
	updates_plot = plot_price_updates(trade['numUpdates'])

	####################################
	## EMAIL SETUP
	####################################

	sender_email = "zqretrace@gmail.com"
	receiver_email = "zqretrace@gmail.com"
	password = "Street1011"

	message = MIMEMultipart("alternative")
	message["Subject"] = f"{ticker} TRADE SUMMARY"
	message["From"] = sender_email
	message["To"] = receiver_email

	text = f"""
	Summary
	{quantity} {action} {ticker} @ {avg_price}

	Profitability
	Risk: ${risk}
	Reward: ${reward}
	Realized: ${realized}
	RunUp: {runup * 100}%
	Drawdown: {drawdown * 100}%

	Behavior
	State: {state}
	Status: {status}
	Trade Lenght: {length}
	Execution Logic: {logic}

	Order Details
	Entry: {entry}
	Profit: {profit}
	Stop: {stop}

	Chronology
	Init: {init}
	Execution: {execution}
	Closing: {closing}
	"""

	html = f"""\
			<html>
			  <body>
			        <b>Summary</b><br>
			        {quantity} {action} {ticker} @ {avg_price}<br>
			        <br>
			        <b>Profitability</b><br>
			        Risk: ${risk}<br>
			        Reward: ${reward}<br>
			        Realized: ${realized}<br>
			        RunUp: {runup}%<br>
			        Drawdown: {drawdown}%<br>
			        <br>
			        <b>Behavior</b><br>
			        State: {state}<br>
			        Status: {status}<br>
			        Trade Length: {length}<br>
			        Execution Logic: {logic}<br>
			        <br>
			        <b>Order Details</b><br>
			        Entry: {entry}<br>
			        Profit: {profit}<br>
			        Stop: {stop}<br>
			        <br>
			        <b>Chronology</b><br>
			        Init: {init}<br>
			        Execution: {execution}<br>
			        Closing: {closing}<br>
			        <br>
			        <b>Plots</b><br>
			        <img src="cid:price_plot">
			        <br><br>
			        <img src="cid:updates_plot">
			        <br>
			        zQ<br>
			        <br>
			  </body>
			</html>
			"""

	## Add text and html options
	part1 = MIMEText(text, "plain")
	part2 = MIMEText(html, "html")

	message.attach(part1)
	message.attach(part2)

	## Attach the images
	msgImage = MIMEImage(price_plot)
	msgImage.add_header('Content-ID', '<price_plot>')
	message.attach(msgImage)

	msgImage = MIMEImage(updates_plot)
	msgImage.add_header('Content-ID', '<updates_plot>')
	message.attach(msgImage)

	# Create secure connection with server and send email
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
	    server.login(sender_email, password)
	    server.sendmail(
	        sender_email, receiver_email, message.as_string()
	    )
	plt.close('all')

if __name__ == '__main__':

	while True:

		actions = []
		files = os.listdir(dir_) ## Get a static list to avoid deleting new data

		for file in files:

			es_doc = np.load(dir_+file)[0]
			if 'marketdata' not in file:

				print('Sending Email.')
				notify_(es_doc['_source'])
				
			actions.append(es_doc)

		helpers.bulk(es, actions)

		## Remove all the files
		for file in files:
			os.unlink(dir_+file)
		
		time.sleep(15)