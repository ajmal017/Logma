import sys, os
import zipfile

from joblib import Parallel, delayed

n = len(os.listdir(os.path.dirname('D:/TickData/')))
dir_ = 'D:/TickData/' 
dir_2 = 'D:/TickData_UZ_FW/' 

for i, file in enumerate(os.listdir(os.path.dirname(dir_))):
	print(i / n)
	print(file)
	print()
	try:
	    with zipfile.ZipFile(dir_+file, 'r') as zip_ref:
	        zip_ref.extractall(dir_2)
	except Exception as e:
		print(e)
		print(file)

