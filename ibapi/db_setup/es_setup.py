from elasticsearch import Elasticsearch
from elasticsearch import helpers

import requests, json

es = Elasticsearch([{"host" : "localhost", "port" : 9200}])

try:
	print(es.indices.delete("retracements"))
except Exception as e:
	print(e)

print(es.indices.create("retracements", body = {
    "settings" : {
        "number_of_shards" : 1,
        "number_of_replicas" : 1
    },
    "mappings" : {
        'properties': {'ticker': {'type': 'keyword'},
    'action': {'type': 'keyword'},
    'direction' : {'type' : 'long'},
    'position': {'type': 'long'},
    'avgCost': {'type': 'double'},
    'initTime': {'type': 'date', 'format': 'date_hour_minute_second'},
    'executionTime': {'type': 'date', 'format': 'date_hour_minute_second'},
    'closingTime': {'type': 'date', 'format': 'date_hour_minute_second'},
    'positionClosed': {'type': 'long'},
    'avgCostOnClose': {'type': 'double'},
    'entryLimitPrice': {'type': 'double'},
    'takeProfitLimitPrice': {'type': 'double'},
    'stopLossLimitPrice': {'type': 'double'},
    'drawdown': {'type': 'double'},
    'runUp': {'type': 'double'},
    'tickIncrement': {'type': 'double'},
    'state': {'type': 'keyword'},
    'status': {'type': 'keyword'},
    'executionLogic': {'type': 'keyword'},
    'timePeriod': {'type': 'long'},
    'maturity': {'type': 'long'},
    'numPeriods': {'type': 'long'}}}
    }))