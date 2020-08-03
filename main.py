import configparser
import subprocess
import time
import logging

conf_file = "config.ini"
logging.basicConfig(filename='main.log',level=logging.DEBUG,format='%(asctime)s %(message)s')

logging.info("LAUNCHING")
running_procs = subprocess.Popen(["accserver.exe"], cwd="./instances/01/",close_fds = True, stdout=subprocess.DEVNULL, stderr=None)
running_procs2 = subprocess.Popen(["accserver.exe"], cwd="./instances/02/",close_fds = True, stdout=subprocess.DEVNULL, stderr=None)

while running_procs:
    status = running_procs.poll()
    if status is not None: # Process finished.
        break
    else: # No process is done, wait a bit and check again.
        time.sleep(1)
        continue

    # Here, `running_procs` has finished with return code `retcode`
    if status != 0:
        """Error handling."""
    print(running_procs.stdout)