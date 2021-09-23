import os.path
import subprocess
import n4d.responses

class LliurexStore:
	
	LLIUREX_VERSION_NOT_FOUND=-20
	LLIUREX_VERSION_ERROR=-20
	
	def install_epi(self,epifile):
		if os.path.exists(epifile):
			try:
				p=subprocess.Popen(["/usr/sbin/epi-gtk","{}".format(epifile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			except Exception as e:
				return n4d.responses.build_failed_call_response(LliurexStore.LLIUREX_VERSION_ERROR,str(e))
	

if __name__=="__main__":
	llstore=LliurexStore()
