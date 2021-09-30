import os.path
import subprocess
import n4d.responses

class LliurexStore:

	EPI_GUI="/usr/sbin/epi-gtk"
	EPI_CLI="/usr/sbin/epic"
	STORE_FILE_ERROR=-10
	STORE_INSTALL_ERROR=-20
	STORE_REMOVE_ERROR=-30
	
	def install_epi(self,epifile,gui):
		if os.path.exists(epifile):
			try:
				if gui:
					p=subprocess.Popen([LliurexStore.EPI_GUI,"{}".format(epifile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				else:
					p=subprocess.Popen([LliurexStore.EPI_CLI,"-u","install","{}".format(epifile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				return n4d.responses.build_successful_call_response(p.pid)
			except Exception as e:
				print(e)
				return n4d.responses.build_failed_call_response(LliurexStore.STORE_INSTALL_ERROR,str(e))
		else:
			return n4d.responses.build_failed_call_response(LliurexStore.STORE_FILE_ERROR,str(e))
	
	def remove_epi(self,epifile,gui):
		if os.path.exists(epifile):
			try:
				if gui:
					p=subprocess.Popen([LliurexStore.EPI_GUI,"{}".format(epifile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				else:
					p=subprocess.Popen([LliurexStore.EPI_CLI,"-u","uninstall","{}".format(epifile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				return n4d.responses.build_successful_call_response(p.pid)
			except Exception as e:
				print(e)
				return n4d.responses.build_failed_call_response(LliurexStore.STORE_REMOVE_ERROR,str(e))
		else:
			return n4d.responses.build_failed_call_response(LliurexStore.STORE_FILE_ERROR,str(e))

if __name__=="__main__":
	llstore=LliurexStore()
