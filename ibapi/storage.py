from collections import deque
from datetime import datetime, timedelta

from tools.zlogging import loggers

class Storage(object):
    
    def __init__(self, ticker, num_periods, time_period):
        
        self.data = deque([], maxlen=num_periods)

        self.ticker = ticker
        self.num_periods = num_periods
        self.time_period = time_period
        
        self.fmt = '%Y%m%d  %H:%M:00'
        self.current_candle = None
        self.logger = loggers[ticker]
        
    def candle_time(self):
        
        dt = datetime.now()
        dt -= timedelta(minutes = dt.minute % self.time_period)
        return dt.strftime(self.fmt)
    
    def update(self, bar):

        n_date, n_open, n_high, n_low, n_close = bar

        if self.current_candle_time == n_date:
            c_date, c_open, c_high, c_low, c_close = self.current_candle
            self.current_candle = (self.current_candle_time, c_open, max(c_high, n_high), min(c_low, n_low), n_close)
        else:
            self.data.append(self.current_candle)
            self.current_candle_time = self.candle_time()
            self.current_candle = (self.current_candle_time, n_open, n_high, n_low, n_close)
            
    def on_period(self):
        
        self.logger.info('TIME: {}~-~{}'.format(self.current_candle[0], self.current_candle_time))
    
    def is_initialized(self):
        
        try:
            self.current_candle = self.data[-1]
            return len(self.data) == self.num_periods
        except:
            return False