from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import smtplib, ssl
import numpy as np
import sys, os, io
import joblib

###################################

es = Elasticsearch([{"host" : "192.168.2.38", "port" : 9200}])
fmt = '%Y-%m-%dT%H:%M:%S'

###################################


def get_trades(n_days):

	query = {
	    "range" : {
	        "initTime" : {
	            "gte" : (datetime.now() - timedelta(days=n_days)).strftime(fmt)
	        }
	    }
	}

	return es.search(index='retracements', body = {"query" : query, "size" : 10000})['hits']['hits']

def report_(trades):

	main = [] 
	for trade in trades:
	    trade = trade['_source']
	    if trade['executionLogic'] == 'NO FILL':
	        main.append([trade['executionLogic'], 0, trade['initTime'],trade['initTime'], trade['direction'], 'N', 0])
	    else:
	        denom = trade['tickIncrement'] * 0.2
	        realized = (trade['direction'] * (trade['avgCostOnClose'] - trade['avgCost'])) / denom
	        excess = realized / trade['candleSize'] - 1 if realized > 0 else realized / (trade['candleSize'] * 2.5) + 1
	        main.append([trade['executionLogic'], realized, trade['initTime'], trade['closingTime'],
	                     trade['direction'], 'G' if realized > 0 else 'L', excess])
	main = pd.DataFrame(main, columns = ['ExecutionLogic', 'Realized', 'Time', 'cTime', 'Direction', 'PnL', 'Excess']).sort_values('Time', ascending=True)
	main['Time'] = pd.to_datetime(main.Time.values)
	main['cTime'] = pd.to_datetime(main.cTime.values)

	## Equity curve
	results = main.Realized.values.cumsum()
	profit = np.maximum(results, 0)
	loss = np.minimum(results, 0)
	ar = np.arange(results.shape[0])

	sns.set(style="darkgrid")
	plt.figure(figsize=(30, 8))
	sns.lineplot(y=results, x=ar, linewidth=0.4, color='b', marker='1')
	plt.axhline(0, color='black', linewidth=0.4)

	plt.fill_between(ar, results, facecolor='green', alpha=0.5, where=profit>0, interpolate=True)
	plt.fill_between(ar, results, facecolor='red', alpha=0.5, where=loss<0, interpolate=True)

	plt.title('Equity Curve', size=18)
	plt.ylabel('$      ', rotation=0, size=18)

	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	equity_curve_plot = img_

	## Excess Return
	fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(30, 8), sharex=True, sharey=True)
	sns.distplot(main[main.PnL == 'G'].Excess.values, vertical=True, ax=ax[1], color='g')
	ax[0].set_title('Excess Loss Distribution', size=15)
	sns.distplot(main[main.PnL == 'L'].Excess.values, vertical=True, ax=ax[0], color='r')
	ax[1].set_title('Excess Gain Distribution', size=15)
	ax[1].axhline(0, color='black')
	ax[0].axhline(0, color='black')

	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	excess_return_plot = img_


	## Sharpe
	rf = 0.02# Yearly
	SECONDS_IN_YEAR = 252 * 24 * 60 * 60
	df = main[main.PnL != 'N']
	df['Factor'] = (df.cTime - df.Time).dt.seconds / SECONDS_IN_YEAR
	df['RF'] = rf
	x = df.Realized / 1000 - df.Factor * df.RF
	sharpe_ratio = x.mean() / x.std()

	## Sortino
	num = df.Realized / 1000 - df.Factor * df.RF
	denom = df[df.Realized < 0].Realized / 1000
	denom = denom.values.std()
	sortino_ratio = num.mean() / denom

	# Profit Factor
	profit_factor = main[main.PnL == 'G'].Realized.sum() / abs(main[main.PnL == 'L'].Realized.sum())

	## Streaks
	results = main[main.PnL != 'N'].Realized.values
	x = np.sign(results)
	maxs = np.maximum(x, 0)
	run = 0
	max_run = 0
	for m in maxs:
	    if m == 0:
	        run = 0
	    else:
	        run += 1
	    max_run = max(run, max_run)
	mins = np.minimum(x, 0)
	run = 0
	max_loss_run = 0
	for m in mins:
	    if m == 0:
	        run = 0
	    else:
	        run += 1
	    max_loss_run = max(run, max_loss_run)
	max_run, max_loss_run

	## Profitability
	gains = main[main.Realized > 0].Realized.values
	losses = main[main.Realized < 0].Realized.values

	max_gain, min_loss = max(gains), min(losses)

	ninty_gain, ninty_loss = np.quantile(gains, 0.9), np.quantile(losses, 0.1)

	avg_winner = gains.mean()
	avg_loser = losses.mean()

	ratio_winner_loser = abs(avg_winner / avg_loser)

	denom = len(gains) + len(losses)
	exp_value = (len(gains) / denom) * avg_winner + (len(losses) / denom) * avg_loser

	all_stats = main.ExecutionLogic.value_counts()
	filled_stats = main[main.ExecutionLogic != 'NO FILL'].ExecutionLogic.value_counts()

	## Pie charts
	stats = []
	for trade in trades:
	    exe_logic = trade['_source']['executionLogic']
	    state = trade['_source']['state']
	    stats.append([exe_logic, state])
	df = pd.DataFrame(stats, columns = ['ExeLogic', 'State'])

	g, r, gr=[plt.cm.Greens, plt.cm.Reds, plt.cm.Greys]
	states = ['WICK', 'NORMAL', 'MATURITY']
	logics = ['HARD STOP', 'TAKE PROFIT', 'SOFT STOP', 'NO FILL']
	colors = {
	    'TAKE PROFIT' : (g, 0.6),
	    'HARD STOP' : (r, 0.9),
	    'SOFT STOP' : (r, 0.65),
	    'NO FILL' : (gr, 0.6)
	}

	group_names, group_sizes, group_colors = [], [], []
	sub_names, sub_sizes, sub_colors = [], [], []

	for logic in logics:
	   
	    if logic in df.ExeLogic.values:
	        
	        tmp = df[df.ExeLogic == logic]
	        
	        group_names.append(logic)
	        group_sizes.append(tmp.shape[0])
	        color, shade = colors[logic]
	        group_colors.append(color(shade))
	    
	        for i, state in enumerate(states):
	            
	            if state in tmp.State.values:
	                
	                sub_names.append(state)
	                sub_sizes.append(tmp[tmp.State == state].shape[0])
	                color, shade = colors[logic]
	                sub_colors.append(color(shade - (i+1)*0.05))

	# First Ring (outside)
	fig, ax = plt.subplots(figsize=(10, 10))
	ax.axis('equal')
	group_sizes = np.array(group_sizes)
	group_sizes = group_sizes / group_sizes.sum()
	mypie, _ = ax.pie(group_sizes, radius=1.1, labels=['%s %.2f%%' % (name, size * 100) for name, size in zip(group_names, group_sizes)], colors=group_colors)
	plt.setp(mypie, width=1, edgecolor='white')

	## Second Ring (Inside)
	mypie2, _ = ax.pie(sub_sizes, radius=.85, labels=sub_names, labeldistance=0.7, colors=sub_colors)
	plt.setp(mypie2, width=0.4, edgecolor='white')
	plt.margins(0,0)

	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	trade_executions_plot = img_

	## Organize the groups
	stats = []
	for trade in trades:
	    exe_logic = trade['_source']['executionLogic']
	    state = trade['_source']['state']
	    stats.append([exe_logic, state])
	df = pd.DataFrame(stats, columns = ['ExeLogic', 'State'])

	g, r, gr=[plt.cm.Greens, plt.cm.Reds, plt.cm.Greys]
	states = ['WICK', 'NORMAL', 'MATURITY']
	logics = ['HARD STOP', 'TAKE PROFIT', 'SOFT STOP']
	colors = {
	    'TAKE PROFIT' : (g, 0.6),
	    'HARD STOP' : (r, 0.9),
	    'SOFT STOP' : (r, 0.65),
	    'NO FILL' : (gr, 0.6)
	}

	group_names, group_sizes, group_colors = [], [], []
	sub_names, sub_sizes, sub_colors = [], [], []

	for logic in logics:
	   
	    if logic in df.ExeLogic.values:
	        
	        tmp = df[df.ExeLogic == logic]
	        
	        group_names.append(logic)
	        group_sizes.append(tmp.shape[0])
	        color, shade = colors[logic]
	        group_colors.append(color(shade))
	    
	        for i, state in enumerate(states):
	            
	            if state in tmp.State.values:
	                
	                sub_names.append(state)
	                sub_sizes.append(tmp[tmp.State == state].shape[0])
	                color, shade = colors[logic]
	                sub_colors.append(color(shade - (i+1)*0.05))

	# First Ring (outside)
	fig, ax = plt.subplots(figsize=(10, 10))
	ax.axis('equal')
	group_sizes = np.array(group_sizes)
	group_sizes = group_sizes / group_sizes.sum()
	mypie, _ = ax.pie(group_sizes, radius=1.1, labels=['%s %.2f%%' % (name, size * 100) for name, size in zip(group_names, group_sizes)], colors=group_colors)
	plt.setp(mypie, width=1, edgecolor='white')

	## Second Ring (Inside)
	mypie2, _ = ax.pie(sub_sizes, radius=.85, labels=sub_names, labeldistance=0.7, colors=sub_colors)
	plt.setp(mypie2, width=0.4, edgecolor='white')
	plt.margins(0,0)

	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	fill_executions_plot = img_

	drawdowns = []
	for trade in trades:
	    trade = trade['_source']
	    
	    if trade['executionLogic'] == 'NO FILL':
	        continue
	    
	    direction = trade['direction']
	    avg_cost = trade['avgCost']
	    avgCostOnClose = trade['avgCostOnClose']
	    dds = []
	    
	    if direction == 1:
	        
	        for date, candle in zip(trade['data']['postDates'], trade['data']['postPrices']):
	            
	            dds.append([date, min((candle[2] - avg_cost) / (trade['tickIncrement'] / 5), 0)])
	            
	        last = dds[-1][0]
	        dt = (datetime.strptime(last, '%Y%m%d  %H:%M:%S') + timedelta(minutes=5)).strftime('%Y%m%d  %H:%M:00')
	        realized = (avgCostOnClose - avg_cost) / ((trade['tickIncrement'] / 5))
	        dds.append([dt, min(realized, 0)])
	        
	    elif direction == -1:
	        
	        for date, candle in zip(trade['data']['postDates'], trade['data']['postPrices']):
	            
	            dds.append([date, min((avg_cost - candle[1]) / (trade['tickIncrement'] / 5), 0)])
	            
	        last = dds[-1][0]
	        dt = (datetime.strptime(last, '%Y%m%d  %H:%M:%S') + timedelta(minutes=5)).strftime('%Y%m%d  %H:%M:00')
	        realized = (avg_cost - avgCostOnClose) / ((trade['tickIncrement'] / 5))
	        dds.append([dt, min(realized, 0)])
	    drawdowns.append(np.array(dds))

	dates = [d[:, 0].tolist() for d in drawdowns]
	dates = [item for sublist in dates for item in sublist]
	mind, maxd = min(dates), max(dates)

	df = pd.DataFrame()
	df['Date'] = pd.date_range(start=mind, end=maxd, freq='5T')

	for dd in drawdowns:
	    d = pd.DataFrame(dd, columns = ['Date', 'Drawdown'])
	    d['Date'] = pd.to_datetime(d.Date.values)
	    df = df.merge(d, on='Date', how='outer')
	df = df.fillna(0)
	var = df.iloc[:, 1:].values.astype(float).sum(axis=1)
	x = np.quantile(var, 0.05)
	var = var[var <= x]

	plt.figure(figsize=(30, 8))
	plt.title('Value at Risk - 5%', size=15)
	sns.distplot(var)
	plt.xlabel('Dollar Drawdown', size=15)

	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	var_plot = img_

	df = pd.DataFrame()
	df['Date'] = pd.date_range(start=mind, end=maxd, freq='5T')

	for dd in drawdowns:
	    d = pd.DataFrame(dd, columns = ['Date', 'Drawdown'])
	    d['Date'] = pd.to_datetime(d.Date.values)
	    df = df.merge(d, on='Date', how='outer')

	df = df.notnull()
	max_consec_trades = df.sum(axis=1).max()

	results = []
	dates = []
	for trade in trades:
	    trade = trade['_source']
	    if trade['executionLogic'] == 'NO FILL':
	        continue
	    denom = trade['tickIncrement'] * 0.2
	    realized = (trade['direction'] * (trade['avgCostOnClose'] - trade['avgCost'])) / denom
	    dates.append(trade['closingTime'])
	    results.append(realized)

	df = pd.DataFrame(list(zip(results, dates)), columns = ['Trade', 'Date'])
	df = df.sort_values('Date', ascending=True)
	df['TID'] = np.arange(df.shape[0])
	df['Date'] = pd.to_datetime(df.Date, format='%Y-%m-%dT%H:%M:%S')
	df['Day'] = df.Date.dt.day_name()
	df['Color'] = ['#3eeb31' if t > 0 else '#f00505' for t in df.Trade.values]

	n_per_group = df.Day.value_counts().max()

	f, ax = plt.subplots(nrows=2, ncols=1, figsize=(30, 8))
	g = sns.barplot(x='Day', y='Trade', data=df, hue='TID', palette=df.Color.values, ax = ax[1])
	g.legend_.remove()

	stats = []
	for day in df.Day.unique():
	    total = df[df.Day == day].Trade.sum()
	    stats.append([day, total, '#3eeb31' if total > 0 else '#f00505'])
	df = pd.DataFrame(stats, columns = ['Day', 'Total', 'Color'])
	g = sns.barplot(x='Day', y='Total', data=df, palette=df.Color.values, ax = ax[0])
	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	daily_profit_breakdown = img_

	results = []
	dates = []
	for trade in trades:
	    trade = trade['_source']
	    if trade['executionLogic'] == 'NO FILL':
	        continue
	    denom = trade['tickIncrement'] * 0.2
	    realized = (trade['direction'] * (trade['avgCostOnClose'] - trade['avgCost'])) / denom
	    dates.append(trade['initTime'])
	    results.append(realized)
	df = pd.DataFrame(list(zip(results, dates)), columns = ['Trade', 'Date'])
	df['Date'] = pd.to_datetime(df.Date, format='%Y-%m-%dT%H:%M:%S')
	df['Day'] = df.Date.dt.day_name()
	df['Hour'] = df.Date.dt.hour
	df = df.sort_values('Date')
	df = df[['Day', 'Hour']]

	days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
	hours_of_day = [i for i in range(24)]
	co = pd.DataFrame(index=days_of_week, columns = hours_of_day).fillna(0)
	for row in df.values:
	    day, hour = row
	    co.loc[day, hour] += 1

	plt.figure(figsize=(30, 8))
	plt.title('Close Time Heatmap')
	sns.heatmap(co.values, cmap='Greys')
	plt.xlabel('Hour of Day')
	plt.yticks(ticks = 0.5+np.arange(len(days_of_week)), labels=days_of_week, rotation=360)

	img_ = None
	with io.BytesIO() as img_bytes:
	    img_bytes = io.BytesIO()
	    plt.savefig(img_bytes, format='jpg')
	    img_bytes.seek(0)
	    img_ = img_bytes.read()
	closetime_heatmap_plot = img_

	####################################
	## EMAIL SETUP
	####################################

	sender_email = "zqretrace@gmail.com"
	receiver_email = "zqretrace@gmail.com, mp0941745@gmail.com"
	receiver_email_list = ["zqretrace@gmail.com", "mp0941745@gmail.com"]
	password = "Street1011"

	message = MIMEMultipart("alternative")
	message["Subject"] = "WEEKLY SUMMARY"
	message["From"] = sender_email
	message["To"] = receiver_email

	text = f"""
	Summary
	{all_stats.__str__()}
	<br>
	{filled_stats.__str__()}

	Profitability
	Sharpe: {sharpe_ratio}
	Max Winning Run: {max_run}
	Max Losing Run: {max_loss_run}
	Max Consec. Active Trades: {max_consec_trades}<br>
	Max Gain: {max_gain}
	Max Loss: {min_loss}
	90% Gain: {ninty_gain}
	10% Loss: {ninty_loss}
	Avg Winner: {avg_winner}
	Avg Loser: {avg_loser}
	Ratio W/L : {ratio_winner_loser}
	Expected Value: {exp_value}
	"""

	html = f"""\
			<html>
			  <body>

			  		<b>Summary</b>
			  		<br><br>
			  		All Trade Stats<br>
					{all_stats.to_frame().to_html()}
					
					<br><br>
					All Filled Stats
					{filled_stats.to_frame().to_html()}
					
					<br><br><br>
					<b>Profitability</b>
					Sharpe: {np.round(sharpe_ratio, 2)}<br>
					Sortino: {np.round(sortino_ratio, 2)}<br>
					Profit Factor: {np.round(profit_factor, 2)}<br>
					Max Winning Run: {np.round(max_run, 2)}<br>
					Max Losing Run: {np.round(max_loss_run, 2)}<br>
					Max Consec. Active Trades: {max_consec_trades}<br>
					Max Gain: ${np.round(max_gain, 2)}<br>
					Max Loss: ${np.round(min_loss, 2)}<br>
					90% Gain: ${np.round(ninty_gain, 2)}<br>
					10% Loss: ${np.round(ninty_loss, 2)}<br><br>
					Avg Winner: ${np.round(avg_winner, 2)}<br>
					Avg Loser: ${np.round(avg_loser, 2)}<br>
					Ratio W/L : {np.round(ratio_winner_loser, 2)}<br>
					Expected Value: ${np.round(exp_value, 2)}<br><br><br>

					<b>Plots</b>
					<img src="cid:equity_curve_plot"><br>
					<img src="cid:daily_profit_breakdown"><br>
					<img src="cid:excess_return_plot"><br>
					<img src="cid:trade_executions_plot">
					<img src="cid:fill_executions_plot"><br>
					<img src="cid:var_plot"><br>
					<img src="cid:closetime_heatmap_plot"><br>
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
	msgImage = MIMEImage(equity_curve_plot)
	msgImage.add_header('Content-ID', '<equity_curve_plot>')
	message.attach(msgImage)
	## Attach the images
	msgImage = MIMEImage(daily_profit_breakdown)
	msgImage.add_header('Content-ID', '<daily_profit_breakdown>')
	message.attach(msgImage)

	msgImage = MIMEImage(excess_return_plot)
	msgImage.add_header('Content-ID', '<excess_return_plot>')
	message.attach(msgImage)

	msgImage = MIMEImage(trade_executions_plot)
	msgImage.add_header('Content-ID', '<trade_executions_plot>')
	message.attach(msgImage)

	msgImage = MIMEImage(fill_executions_plot)
	msgImage.add_header('Content-ID', '<fill_executions_plot>')
	message.attach(msgImage)

	msgImage = MIMEImage(var_plot)
	msgImage.add_header('Content-ID', '<var_plot>')
	message.attach(msgImage)

	msgImage = MIMEImage(closetime_heatmap_plot)
	msgImage.add_header('Content-ID', '<closetime_heatmap_plot>')
	message.attach(msgImage)

	# Create secure connection with server and send email
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
	    server.login(sender_email, password)
	    server.sendmail(
	        sender_email, receiver_email_list, message.as_string()
	    )
	plt.close('all')

if __name__ == '__main__':

	report_(get_trades(7))