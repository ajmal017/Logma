from pathlib import Path
import os

main_dir = Path('D:/AlgoMLData')
trades_dir = main_dir/'AddTradesIB'
features_dir = main_dir/'FeaturesIB'
scaled_dir = main_dir/'ScaledIB'
data_dir = main_dir/'DataIB'
scaler_dir = main_dir/'ScalersIB'

for path in [main_dir, trades_dir, features_dir, scaled_dir, data_dir, scaler_dir]:

	if not os.path.isdir(path):
		os.mkdir(path)