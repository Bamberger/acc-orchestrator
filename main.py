import configparser
import subprocess
import time
import logging

conf_file = "config.ini"
logging.basicConfig(filename='main.log',level=logging.DEBUG,format='%(asctime)s %(message)s')

def startInstance(instance_id):
    process = subprocess.Popen(["accserver.exe"], cwd="./instances/" + str(instance_id) + "/",close_fds = True, stdout=subprocess.DEVNULL, stderr=None)
    return process.pid

## Parse config file
logging.info("Reading from config file: " + str(conf_file))
config = configparser.ConfigParser() # Init ConfigParser
config.read(conf_file) # Parse the config file
c_instance_limit = int(config.get('general', 'instance_limit')) # Get instance limit from config
logging.info("Instance limit loaded from config file, Instance limit is: " + str(c_instance_limit))

instance_iter = 1
instance_status =	{}
while (instance_iter <= c_instance_limit):
    instance_status[instance_iter] = {
        "status": "available",
        "pid": 0
    }
    instance_iter += 1
    print(instance_status)

startInstance(1)

# running_procs = subprocess.Popen(["accserver.exe"], cwd="./instances/1/",close_fds = True, stdout=subprocess.DEVNULL, stderr=None)
# running_procs2 = subprocess.Popen(["accserver.exe"], cwd="./instances/2/",close_fds = True, stdout=subprocess.DEVNULL, stderr=None)

# while running_procs:
#     status = running_procs.poll()
#     if status is not None: # Process finished.
#         break
#     else: # No process is done, wait a bit and check again.
#         time.sleep(1)
#         continue

#     # Here, `running_procs` has finished with return code `retcode`
#     if status != 0:
#         """Error handling."""
#     print(running_procs.stdout)