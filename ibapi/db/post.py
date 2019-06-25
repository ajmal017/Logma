from elasticsearch import helpers
from es_setup import es
import numpy as np
import sys, os
import time

dir_ = 'dumps/'

if __name__ == '__main__':

	while True:

		actions = []
		files = os.listdir(dir_) ## Get a static list to avoid deleting new data
		for file in files:
			x = np.load(dir_+file)
			actions.extend(x.copy().tolist())
		helpers.bulk(es, actions)

		## Remove all the files
		for file in files:
			os.unlink(dir_+file)

		time.sleep(10)