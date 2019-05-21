from collections import deque
from datetime import datetime, timedelta

class Storage(object):
    
    def __init__(self, ticker, num_periods, time_period):
        
        self.data = deque([], maxlen=num_periods)

        self.ticker = ticker
        self.num_periods = num_periods
        self.time_period = time_period
        
        self.fmt = '%Y%m%d  %H:%M:00'
        
        self.current_candle_time = self.candle_time()
        self.current_candle = None
        
    def candle_time(self):
        
        dt = datetime.now()
        dt -= timedelta(minutes = dt.minute % self.time_period)
        return dt.strftime(self.fmt)
    
    def update(self, bar):
        if self.current_candle_time == bar.date:
            self.current_candle = bar
            
    def on_period(self):
        
        self.append(self.current_candle)
        print(self.ticker, self.current_candle.date, self.current_candle.open, self.current_candle.high, self.current_candle.low, self.current_candle.close)
        self.current_candle_time = self.candle_time()
        
    def append(self, bar):

        self.data.append((bar.date, bar.open, bar.high, bar.low, bar.close))
    
    def is_initialized(self):
        
        self.current_candle = self.data[-1]
        return len(self.data) == self.num_periods