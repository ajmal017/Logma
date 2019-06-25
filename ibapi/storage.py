from collections import deque
from datetime import datetime, timedelta

from tools.zlogging import loggers, post_market_data_doc

class Storage(object):
    
    def __init__(self, ticker, num_periods, time_period, scanner_job):
        
        ## Add one for the cummulative product calculation for Long & Short Progressions
        self.data = deque([], maxlen=num_periods + 1)

        self.ticker = ticker
        self.num_periods = num_periods
        self.time_period = time_period
        
        self.fmt = '%Y%m%d  %H:%M:00'
        self.current_candle = None
        self.logger = loggers[ticker]
        self.new_candle = False

        self.scanner_job = scanner_job

    def aggregate_candle(self, n_open, n_high, n_low, n_close):

        c_date, c_open, c_high, c_low, c_close = self.current_candle
        self.current_candle = (self.current_candle_time, c_open, max(c_high, n_high), min(c_low, n_low), n_close)
    
    def update(self, bar):

        ## Get all constituents to see what to do
        n_date, n_open, n_high, n_low, n_close = bar
        c_time = self.candle_time()

        if c_time != self.convert_unix(n_date):

            ## Aggregate the candle & Push to stack (last data point)
            self.aggregate_candle(n_open, n_high, n_low, n_close)
            self.data.append(self.current_candle)
            
            ## Update the current candle time
            self.current_candle_time = c_time
            self.new_candle = True

            ## Push data through our model
            self.scanner_job()

            data_type = 'nextCandle'

        elif self.new_candle:

            self.current_candle = (self.convert_unix(n_date), n_open, n_high, n_low, n_close)
            self.new_candle = False

            data_type = 'newCandle'

        else:

            ## Aggregate the candle
            self.aggregate_candle(n_open, n_high, n_low, n_close)

            data_type = 'aggCandle'

        #post_market_data_doc(self.ticker, self.time_period, n_date, data_type, (n_open, n_high, n_low, n_close))
            
    def candle_time(self):
        
        dt = datetime.now()
        dt -= timedelta(minutes = dt.minute % self.time_period)
        return dt.strftime(self.fmt)

    def convert_unix(self, unix_timestamp):

        return (datetime.utcfromtimestamp(unix_timestamp - unix_timestamp % (60 * self.time_period)) - timedelta(hours=4)).strftime(self.fmt)