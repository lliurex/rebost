import os,shutil
import subprocess
import n4d.responses
import n4d.server.core as n4dcore

class Rebost:

	EPI_GUI="/usr/sbin/epi-gtk"
	EPI_CLI="/usr/sbin/epic"
	STORE_FILE_ERROR=-10
	STORE_INSTALL_ERROR=-20
	STORE_REMOVE_ERROR=-30

	def __init__(self):
		self.core=n4dcore.Core.get_core()
		self.n4dkey=''

	def remote_install(self,episcript,gui):
		apachePath="/var/www/llx-remote"
		scriptname=os.path.basename(episcript)
		if os.path.exists(apachePath)==True:
			destPath=os.path.join(apachePath,scriptname)
			shutil.copy(episcript,destPath)
			self._get_n4d_key()
			core=n4dcore.Core.get_core()
			remoteVar=self.core.get_variable("LLX_REMOTE_INSTALLER").get('return',{})
			if remoteVar:
				#Send file to apache dir as expected by remote-installer, then update remote-installer
				lines=subprocess.Popen(["LAGUAGE=en_EN; md5sum %s | awk '{print $1}'"%episcript],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
				for line in lines.splitlines():
					md5=line.decode('utf-8')
				pkg_tupla=[episcript,md5]
				url='http://server/llx-remote/'
				if remoteVar.get('sh',[]):
					packages=remoteVar['sh'].get('packages',[])
					if packages==None:
						packages=[]
					packages.append((scriptname,md5))
					packagesSet=[]
					packagesAdded=[]
					for pkgtuple in packages:
						pkg=''
						if isinstance(pkgtuple,tuple):
							pkg,md5=pkgtuple
							if pkg not in packagesAdded:
								packagesAdded.append(pkg)
								packagesSet.append((pkg,md5))

					remoteVar['sh'].update({'packages':packagesSet})
				else:
					remoteVar.update({'sh':{'url':url,'packages':[scriptname]}})
				result=self.core.set_variable("LLX_REMOTE_INSTALLER",remoteVar)
			return n4d.responses.build_successful_call_response()
		
	def _get_n4d_key(self):
		self.n4dkey=''
		with open('/etc/n4d/key') as file_data:
			self.n4dkey = file_data.readlines()[0].strip()
	
	#def _get_n4d_key

	def install_epi(self,epifile,gui):
		if os.path.exists(epifile):
			try:
				p=subprocess.Popen([Rebost.EPI_CLI,"-nc","-u","install","{}".format(epifile)],close_fds=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				return n4d.responses.build_successful_call_response(p.pid)
			except Exception as e:
				print(e)
				return n4d.responses.build_failed_call_response(Rebost.STORE_INSTALL_ERROR,str(e))
		else:
			return n4d.responses.build_failed_call_response(Rebost.STORE_FILE_ERROR,str(e))
	
	def remove_epi(self,epifile,gui):
		if os.path.exists(epifile):
		    try:
		    	p=subprocess.Popen([Rebost.EPI_CLI,"-nc","-u","uninstall","{}".format(epifile)],close_fds=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		    	return n4d.responses.build_successful_call_response(p.pid)
		    except Exception as e:
		    	print(e)
		    	return n4d.responses.build_failed_call_response(Rebost.STORE_REMOVE_ERROR,str(e))
		else:
			return n4d.responses.build_failed_call_response(Rebost.STORE_FILE_ERROR,str(e))

if __name__=="__main__":
	rebost=Rebost()
