from apscheduler.schedulers.background import BlockingScheduler

from zmodel import Model

from datetime import datetime
from threading import Thread
import time

class Instrument(Thread):

    n_times_per_second = 10
    
    def __init__(self, ticker, time_period, short_num_periods, num_periods, manager, storage):

        Thread.__init__(self)
        
        ## Book keeping
        self.ticker = ticker
        self.time_period = time_period
        self.short_num_periods = short_num_periods
        
        ## Evaluation granularity
        self.n_micros = int(1e6 / self.n_times_per_second)
        
        ## Get ML Model
        self.model = Model(ticker = ticker, short_num_periods = short_num_periods, num_periods = num_periods)
        
        ## Storage object for historical data
        self.storage = storage
        
        ## Manager to execute trades
        self.manager = manager
        
    def scanner_job(self):
    
        ## Update the storage object
        self.storage.on_period()

        if self.ticker not in self.manager.trades:

            ## Evaluate the current candle for a signal
            signal, features, direction, price = self.model.is_trade(list(self.storage.data))

            ## Start a trade if we have a signal
            if signal:

                ## Initiate the trade via the order manager
                self.manager.on_signal(direction = direction, quantity = 20000, symbol = self.ticker, price = price)

                ## Pause the scanner job
                #self.blocker.pause('scanner_job')

                ## Resume the manager job
                self.blocker.resume_job('manager_job')
            
    def manager_job(self):
    
        ## Check that the position hasnt been closed / not filled
        if self.ticker in self.manager.trades:

            self.manager.trades[self.ticker].on_period()

        ## Trade has been removed aka closed or not filled
        else:

            # Pause the current job
            self.blocker.pause_job('manager_job')

            # Resume the scanner job
            #self.blocker.resume('scanner_job')
            
    def microsecond_job(self, job_func, params):
        
        micros = datetime.now().microsecond
        
        while int(micros / self.n_micros) < self.n_times_per_second - 1:
            
            job_func(*params)
            
            micros = datetime.now().microsecond
            time.sleep(1.0 / self.n_times_per_second)
    
    def run(self):
        
        ## Scheduler to run
        job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        self.blocker = BlockingScheduler(job_defaults = job_defaults)
        self.blocker.add_job(self.manager_job, 'cron', second='*', id='manager_job', next_run_time=None)
        self.blocker.add_job(self.scanner_job, 'cron', minute='*/{}'.format(self.time_period), id='scanner_job')
        
        self.blocker.start()

    def on_close(self):

        self.blocker.shutdown()
        self.join()