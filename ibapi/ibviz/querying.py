from elasticsearch import Elasticsearch
es = Elasticsearch([{"host" : "192.168.2.38", "port" : 9200}])

def query(filters):
    if len(filters) == 0:
        doc_ = {
            "size" : 10000,
            "query" : {
                "match_all" : {}
            }
        }
    else:
        doc_ = {
            "size" : 10000,
            "query" : {
                "bool" : {
                    "filter" : [
                        *filters
                    ]
                }
            },
        }
    return aggregations(doc_)

def term_query(field, value):
    return {
        "term" : {
            field : {
                "value" : value
            }
        }
    }

def terms_query(field, value):

    return {
            "terms" : {
                field : value
            }
        }

def time_query(lower, upper):
    return {
        "range" : {
            "initTime" : {
                "gte" : "{}T00:00:00".format(lower) if lower is not None else None,
                "lte" : "{}T23:59:00".format(upper) if upper is not None else None
            }
        }
    }

def aggregations(dict_): 
    dict_["aggs"] = {
        "executionLogicAggs" : {
            "terms" : {
                "field" : "executionLogic"
            }
        },
        "directionAggs" : {
            "terms" : {
                "field" : "action"
            }
        },
        "statusAggs" : {
            "terms" : {
                "field" : "status"
            }
        },
        "tickerAggs" : {
            "terms" : {
                "field" : "ticker"
            }
        },
        "stateAggs" : {
            "terms" : {
                "field" : "state"
            }
        }
    }
    return dict_