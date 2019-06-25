from threading import Thread
import threading
import ctypes 
import time

class DashThread(Thread):

	def __init__(self, app):

		Thread.__init__(self)
		self.app = app

	def run(self):

		try:
			self.app.run_server(host='0.0.0.0', debug=False)
		except:
			print('App closed.')

	def get_id(self): 
  
		# returns id of the respective thread 
		if hasattr(self, '_thread_id'): 
			return self._thread_id 
		for id, thread in threading._active.items(): 
			if thread is self: 
				return id
   
	def raise_exception(self): 
		thread_id = self.get_id() 
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 
			  ctypes.py_object(SystemExit)) 
		if res > 1: 
			ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
			print('Exception raise failure')