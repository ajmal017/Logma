import numpy as np
import pandas as pd
import joblib

from scipy.stats import kurtosis
from scipy.stats import skew
from entropy import *
from statsmodels.tsa.stattools import adfuller
from sklearn.preprocessing import StandardScaler

class Model(object):

    model_path = '/home/zquantz/Documents/Models/lgbm_2019-04-16'
    scaling_dir = '/home/zquantz/Documents/Scalers'
    log_trim = 7

    def __init__(self, ticker, short_num_periods, num_periods):
        
        self.ticker = ticker
        self.short_num_periods = short_num_periods
        self.num_periods = num_periods
        
        with open('{}/{}'.format(Model.scaling_dir, ticker), 'rb') as file:
            self.scalers = joblib.load(file)
            
        self.load_model()
        
        self.us = {i : 1 - (i - 12) / 9 for i in range(12, 20)}
        self.eur = {i : 1 - (i - 7) / 9 for i in range(7, 16)}
        self.asia = {i : 1 - (i + 1) / 9 for i in range(0, 9)}
        self.asia[23] = 1

    def load_model(self):
        
        with open(Model.model_path, 'rb') as file:
            self.predictor = joblib.load(file)
        
    def log_trimming(self, x):
        
        cutoff_lt, cutoff_gt = -self.log_trim, self.log_trim
        
        if x > cutoff_gt:
            x = cutoff_gt + np.log(x - cutoff_gt + 1)
        elif x < cutoff_lt:
            x = cutoff_lt - np.log(abs(x) - abs(cutoff_lt) + 1)
        return x

    def iqr_trimming(self, x, feature):
        
        lower_fence, upper_fence = self.scalers[feature]
        
        if x > upper_fence:
            x = upper_fence + x/100
        elif x < lower_fence:
            x = lower_fence - x/100
        return x
    
    def is_signal(self, sig20, sig30, sig50):
        
        return sig30 & sig50
    
    def predict(self, X):
        
        return self.predictor.predict(X)
        
    def is_trade(self, data):

        dfe = pd.DataFrame(data, columns=['Datetime', 'Open', 'High', 'Low', 'Close'])
        dfe.describe()
        df = dfe.iloc[1:, :].copy()
        
        df['Hour'] = pd.to_datetime(df.Datetime).dt.hour
        df['Change'] = (df.Close - df.Open) / df.Open
        change = df.Change.values[-1]
        
        sig50std = df.Change.std()
        sig30std = df.Change[-30:].std()
        sig20std = df.Change[-20:].std()
        
        sig50mean = df.Change.mean()
        sig30mean = df.Change[-30:].mean()
        sig20mean = df.Change[-20:].mean()
        
        sig20 = 1 if change > sig20mean + 3*sig20std else 1 if change < sig20mean - 3*sig20std else 0
        sig30 = 1 if change > sig30mean + 3*sig30std else 1 if change < sig30mean - 3*sig30std else 0
        sig50 = 1 if change > sig50mean + 3*sig50std else 1 if change < sig50mean - 3*sig50std else 0
        
        if self.is_signal(sig20, sig30, sig50):
            
            direction = np.sign(change)*-1
            
            change = self.log_trimming(self.iqr_trimming(change, 'change'))

            dfs = df.iloc[-self.short_num_periods:, :]

            ## Distribution Statistics
            long_vol = np.log(1e-8+(df.Change.std() / np.sqrt(self.num_periods)))
            short_vol = np.log(1e-8+(dfs.Change.std() / np.sqrt(self.short_num_periods)))

            long_skew = df.Change.skew()
            short_skew = dfs.Change.skew()

            long_kurtosis = kurtosis(df.Change.values)
            short_kurtosis = kurtosis(dfs.Change.values)
            
            dlongsma = dfe.Close / dfe.Close.rolling(window=self.num_periods, min_periods=1).mean()
            dlongsma = dlongsma.values[-1]
            dlongsma = self.log_trimming(self.iqr_trimming(dlongsma, 'dlongsma'))

            dshortsma = dfe.Close / dfe.Close.rolling(window=self.short_num_periods, min_periods=1).mean()
            dshortsma = dshortsma.values[-1]
            dshortsma = self.log_trimming(self.iqr_trimming(dshortsma, 'dshortsma'))

            dfe.Close = dfe.Close.pct_change() + 1

            # Market Sessions
            hour = df.Hour.values[-1]
            us_time = self.us[hour] if hour in self.us else 0
            eur_time = self.eur[hour] if hour in self.eur else 0
            asia_time = self.asia[hour] if hour in self.asia else 0
            
            longprog = dfe.Close.values[1:].cumprod()[-1]
            longprog = self.log_trimming(self.iqr_trimming(longprog, 'longprog'))

            shortprog = dfe.Close.values[-self.short_num_periods:].cumprod()[-1]
            shortprog = self.log_trimming(self.iqr_trimming(shortprog, 'shortprog'))

            longspec = spectral_entropy(df.Change.values, sf=self.num_periods, method='welch', nperseg=(self.num_periods/8), normalize=True)
            
            longape = app_entropy(df.Change.values.copy(), order=2, metric='chebyshev')
            shortape = app_entropy(dfs.Change.values.copy(), order=2, metric='chebyshev')

            long_ac = df.Change.autocorr(11)
            short_ac = dfs.Change.autocorr(11)

            t, _, _, _, t_crit, _ = adfuller(df.Change.values, autolag = 'AIC')
            t_crit = list(t_crit.values())[1]
            long_stat =  0 if (t < t_crit or np.isnan(t)) else 1

            t, _, _, _, t_crit, _ = adfuller(dfs.Change.values, autolag = 'AIC')
            t_crit = list(t_crit.values())[1]
            short_stat = 0 if (t < t_crit or np.isnan(t)) else 1

            feats = np.array([direction, abs(sig20), abs(sig30), abs(sig50), change, long_vol, short_vol, long_skew, short_skew, long_kurtosis, short_kurtosis,
                    dlongsma, dshortsma, asia_time, us_time, eur_time, longprog, shortprog, longape, shortape, longspec, long_ac,
                    short_ac, long_stat, short_stat])

            exclude = [0, 1, 2, 3, 13, 14, 15, 23, 24]
            include = [i for i in range(feats.shape[0]) if i not in exclude]

            feats[include] = self.scalers['ss'].transform([feats[include]])

            return self.predict([feats])[0], feats.tolist(), 1, df.Close.values[-1]

        else:

            return 0, [], 0, 0