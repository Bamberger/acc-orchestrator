import configparser
import subprocess
import time
import logging
import os
import json
import psutil

acco_conf_file = "config.ini"
excluded_files = ['acco_default.json', 'configuration.json', 'current']
logging.basicConfig(filename='main.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')


def startInstance(serverconfig="default"):
    # Function to start an accServer instance, this will clear all the directories and start the instance
    logging.info("Instance start called")
    instance_id = 0

    # Select an instance to start
    for instance in instance_status:
        if (instance_status[instance]["status"] == "available"):
            instance_id = instance

    # If no available instance found, close any available default instance
    if instance_id == 0:
        for instance in instance_status:
            if (instance_status[instance]["config"] == "default"):
                instance_id = instance
                stopInstance(instance_id)

    # If no instances available, error and break
    if instance_id == 0:
        logging.error("Instance start called but no available instances")
        return

    # Clear any existing config files
    cfg_dir = os.listdir("./instances/" + str(instance_id) + "/cfg/")
    for curr_file in cfg_dir:
        if curr_file not in excluded_files:
            os.remove("./instances/" + str(instance_id) +
                      "/cfg/" + str(curr_file))
            # print(os.listdir("./instances/" + str(instance_id) + "/cfg/"))
    logging.info("Config directory cleared for instance ID: "+str(instance_id))

    # If serverconfig not provided, load default from acco_default.json
    default = False
    if (serverconfig == "default"):
        default = True
        logging.info("Using default config for instance ID: "+str(instance_id))
        with open("./instances/" + str(instance_id) + "/cfg/acco_default.json") as json_file:
            serverconfig = json.load(json_file)

    # Create config files from serverconfig
    for config_file in serverconfig:
        if config_file not in excluded_files:
            with open("./instances/" + str(instance_id) + "/cfg/" + str(config_file), 'w') as fp:
                json.dump(serverconfig[config_file], fp)

    process = subprocess.Popen(["accserver.exe"], cwd="./instances/" + str(
        instance_id) + "/", close_fds=True, stdout=subprocess.DEVNULL, stderr=None)
    # Update instance_status
    instance_status[instance_id]["pid"] = process.pid
    instance_status[instance_id]["status"] = "running"
    if (default == True):
        instance_status[instance_id]["config"] = "default"
    else:
        instance_status[instance_id]["config"] = str(
            serverconfig["acco.json"]["eventId"])
        instance_status[instance_id]["timeEnd"] = int(
            serverconfig["acco.json"]["timeEnd"])
        instance_status[instance_id]["serverName"] = str(serverconfig["settings.json"]["serverName"])

    # Wait up to 30 seconds and confirm instance is started
    timer = 0
    while (psutil.pid_exists(process.pid) == False):
        if (timer >= 30):
            break
        timer += 1
        time.sleep(1)

    # If instance is not running, log an error and update instance_status
    if (psutil.pid_exists(process.pid) == False):
        logging.error("Failed to start instance ID "+str(instance_id))
        instance_status[instance_id]["pid"] = 0
        instance_status[instance_id]["status"] = "available"
        instance_status[instance_id]["config"] = 0
        instance_status[instance_id]["timeEnd"] = 0
        instance_status[instance_id]["serverName"] = 0
    else:
        logging.info("Succesfully started instance ID "+str(instance_id) +
                     " Status: " + str(instance_status[instance_id]))


def stopInstance(instance_id):
    # Function to stop an instance ID and upload results
    logging.info("Instance stop called for instance ID: " + str(instance_id))

    # Determine pid and kill
    pid = instance_status[instance_id]["pid"]
    p = psutil.Process(pid)
    psutil.Process.kill(p)

    # Wait to confirm instance is stopped
    timer = 0
    while (psutil.pid_exists(pid) == True):
        if (timer >= 30):
            logging.error("Failed to stop instance ID:  "+str(instance_id))
            return
        timer += 1
        time.sleep(1)
    
    # Save any results files
    # TODO Upload results to DB instead of file move
    results_dir = "./instances/" + str(instance_id) + "/results/"
    for results_file in os.listdir(results_dir):
        os.rename(str(results_dir + results_file),"./results/"+str(results_file))

    # Update instance status
    if (psutil.pid_exists(pid) == False):
        logging.info("Succesfully stopped instance ID:  "+str(instance_id))
        instance_status[instance_id]["pid"] = 0
        instance_status[instance_id]["status"] = "available"
        instance_status[instance_id]["config"] = 0
        instance_status[instance_id]["timeEnd"] = 0
        instance_status[instance_id]["serverName"] = 0


def eventCheck(serverconfig):
    # Helper to check if an event is running and if not launch it
    now = time.time()

    # Catch to avoid starting if already running
    running_check = False
    for instance in instance_status:
        if (instance_status[instance]["config"] == serverconfig["acco.json"]["eventId"]):
            running_check = True

    # Call instance start for serverconfig if:
    # 1. Start time is in the past
    # 2. End time is in the future
    # 3. Status is "scheduled"
    if int(serverconfig["acco.json"]["timeStart"]) <= now and int(serverconfig["acco.json"]["timeEnd"]) >= now and str(serverconfig["acco.json"]["eventStatus"]) == "scheduled" and running_check == False:
        startInstance(serverconfig)


# Stop any existing accserver.exe instances
os.system("taskkill /f /im  accServer.exe")

# Parse config file
logging.info("Reading from config file: " + str(acco_conf_file))
config = configparser.ConfigParser()  # Init ConfigParser
config.read(acco_conf_file)  # Parse the config file
# Get instance limit from config
c_instance_limit = int(config.get('general', 'instance_limit'))
# Get default lobbies flag from config
c_default_lobbies = str(config.get('general', 'default_lobbies'))
logging.info(
    "Instance limit loaded from config file, Instance limit is: " + str(c_instance_limit))

# Construct instance_status dict
instance_iter = 1
instance_status = {}
while (instance_iter <= c_instance_limit):
    instance_status[instance_iter] = {
        "status": "available",
        "pid": 0,
        "config": 0,
        "timeEnd": 0,
        "serverName": 0
    }
    instance_iter += 1
logging.info("Instance status: " + str(instance_status))


# Main service loop
while True:
    # Look for events to stop
    now = time.time()
    for instance_id in instance_status:
        if (instance_status[instance_id]["timeEnd"] <= now and instance_status[instance_id]["status"] == "running" and instance_status[instance_id]["config"] != "default"):
            stopInstance(instance_id)

    # Look for instances with no running pid
    # TODO this...

    # Look for events to start
    # TODO Implement DB or API integration
    for event_file in os.listdir("./events/"):
        if event_file.endswith(".json"):
            with open("./events/" + event_file) as serverconfig_file:
                serverconfig = json.load(serverconfig_file)
                # Call the event check and launch function
                eventCheck(serverconfig)
    
    time.sleep(5)

    # If no scheduled events left and default lobbies configured, start Default settings on any available instances
    if (c_default_lobbies == "True"):
        for instance_num in instance_status:
            if (instance_status[instance_num]["status"] == "available"):
                logging.info(
                    "Instance slot available, starting default ")
                startInstance()

    logging.info("Instance status: " + str(instance_status))
    time.sleep(5)