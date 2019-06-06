from apscheduler.schedulers.background import BlockingScheduler

from model import Model
from tools.zlogging import loggers

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
        self.n_micros = int(1e6 / self.n_times_per_second)

        self.model = Model(ticker = ticker, short_num_periods = short_num_periods, num_periods = num_periods)
        self.storage = storage
        self.manager = manager
        self.logger = loggers[ticker]
        
    def scanner_job(self):
    
        self.storage.on_period()

        if self.ticker not in self.manager.trades:

            signal, features, direction, price = self.model.is_trade(list(self.storage.data))

            if False:

                data = {
                    "historical" : list(self.storage.data),
                    "features" : features
                }

                self.manager.on_signal(direction = 1, quantity = 20000, symbol = self.ticker, price = self.storage.data[-1][-1], data = data)

                self.logger.info('JOB: Starting Manager')
                self.blocker.resume_job('manager_job')
            
    def manager_job(self):
    
        if self.ticker in self.manager.trades:

            self.manager.trades[self.ticker].on_period()

        else:

            self.logger.info('JOB: Stopping Manager')
            self.blocker.pause_job('manager_job')
            
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