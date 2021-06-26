import configparser
import subprocess
import time
import logging
import os
import json
import psutil
import pymongo
from bson import json_util

acco_conf_file = "config.ini"
excluded_files = ['acco_default.json', 'configuration.json', 'current', '_id']
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
                break

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
    # If remote mode is True, update DB to flag event as assigned
    elif c_remote_mode == 'True':
        print(serverconfig["acco"])
        query = {"acco.eventId": serverconfig["acco"]["eventId"]}
        newvalues = {"$set": {"acco.eventStatus": "assigned",
                              "acco.host": c_host_id, "acco.lastUpdate": time.time()}}
        col_events.update_one(query, newvalues)

    # Create config files from serverconfig
    for config_file in serverconfig:
        if config_file not in excluded_files:
            with open("./instances/" + str(instance_id) + "/cfg/" + str(config_file) + ".json", 'w') as fp:
                json.dump(serverconfig[config_file], fp)

    process = subprocess.Popen(["accserver.exe"], cwd="./instances/" + str(
        instance_id) + "/", close_fds=True, stdout=subprocess.DEVNULL, stderr=None)
    # Update instance_status
    instance_status[instance_id]["pid"] = process.pid
    instance_status[instance_id]["status"] = "running"
    if (default == True):
        instance_status[instance_id]["config"] = "default"
        instance_status[instance_id]["serverName"] = str(
            serverconfig["settings"]["serverName"])
    else:
        instance_status[instance_id]["config"] = str(
            serverconfig["acco"]["eventId"])
        instance_status[instance_id]["timeEnd"] = int(
            serverconfig["acco"]["timeEnd"])
        instance_status[instance_id]["serverName"] = str(
            serverconfig["settings"]["serverName"])

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
        if c_remote_mode == 'True':
            query = {"acco.eventId": serverconfig["acco"]["eventId"]}
            newvalues = {"$set": {"acco.eventStatus": "scheduled",
                                  "acco.host": "", "acco.lastUpdate": ""}}
            col_events.update_one(query, newvalues)
    else:
        if c_remote_mode == 'True':
            query = {"acco.eventId": serverconfig["acco"]["eventId"]}
            newvalues = {"$set": {"acco.eventStatus": "running",
                                  "acco.host": c_host_id, "acco.lastUpdate": time.time()}}
            col_events.update_one(query, newvalues)
        logging.info("Succesfully started instance ID "+str(instance_id) +
                     " Status: " + str(instance_status[instance_id]))

    logging.info("Instance status: " + str(instance_status))


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
        try:
            if c_remote_mode == 'True':
                with open(str(results_dir + results_file)) as result:
                    # TODO: Something is broken here, I think it's the ACC JSON results files? It fails to parse but may only be with junk files?
                    result_json = json.load(result)
                    print(result_json)
                    col_results.insert_one(result_json)

            elif c_backup_results == 'True':
                os.rename(str(results_dir + results_file),
                          "./results/"+str(results_file))
            os.remove(str(results_dir + results_file))
        except:
            logging.error(
                "failed to process result file, moving to results_errors: " + str(results_dir + results_file))
            os.rename(str(results_dir + results_file),
                      "./results_errors/"+str(results_file))

    # Update instance status
    if (psutil.pid_exists(pid) == False):
        if c_remote_mode == 'True':
            query = {"acco.eventId": serverconfig["acco"]["eventId"]}
            newvalues = {"$set": {"acco.eventStatus": "finished",
                                  "acco.host": c_host_id, "acco.lastUpdate": time.time()}}
            col_events.update_one(query, newvalues)
        logging.info("Succesfully stopped instance ID:  "+str(instance_id))
        instance_status[instance_id]["pid"] = 0
        instance_status[instance_id]["status"] = "available"
        instance_status[instance_id]["config"] = 0
        instance_status[instance_id]["timeEnd"] = 0
        instance_status[instance_id]["serverName"] = 0

    logging.info("Instance status: " + str(instance_status))


def eventCheck(serverconfig):
    # Helper to check if an event is running and if not launch it
    now = time.time()

    # Catch to avoid starting if already running
    running_check = False
    for instance in instance_status:
        if (instance_status[instance]["config"] == serverconfig["acco"]["eventId"]):
            running_check = True

    # Call instance start for serverconfig if:
    # 1. Start time is in the past
    # 2. End time is in the future
    # 3. Status is "scheduled"
    if int(serverconfig["acco"]["timeStart"]) <= now and int(serverconfig["acco"]["timeEnd"]) >= now and str(serverconfig["acco"]["eventStatus"]) == "scheduled" and running_check == False:
        startInstance(serverconfig)


# Stop any existing accserver.exe instances
os.system("taskkill /f /im  accServer.exe")


# Parse config file
logging.info("Reading from config file: " + str(acco_conf_file))
config = configparser.ConfigParser()  # Init ConfigParser
config.read(acco_conf_file)  # Parse the config file
# Get instance limit from config
c_instance_limit = int(config.get('general', 'instance_limit'))
logging.info(
    "Instance limit loaded from config file, Instance limit is: " + str(c_instance_limit))
# Get default lobbies flag from config
# TODO This should be bool? I think this broke somehow earlier
c_default_lobbies = str(config.get('general', 'default_lobbies'))
# Get backup_results flag from config
c_backup_results = str(config.get('general', 'backup_results'))
# Get host_id
c_host_id = str(config.get('general', 'host_id'))
logging.info("Host ID: "+str(c_host_id))
# Get remote mode flag from config
# TODO This should be bool? I think this broke somehow earlier
c_remote_mode = str(config.get('general', 'remote_mode'))
# If remote mode is True, get mongodb URI
if (c_remote_mode) == 'True':
    c_mongo_uri = str(config.get('mongodb', 'mongo_uri'))
    mongo_client = pymongo.MongoClient(c_mongo_uri)
    host_info = mongo_client['HOST']
    logging.info("mongo connection established, host:" + str(host_info))
    db = mongo_client.acc_orchestrator
    col_events = db.events
    col_results = db.results

# If remote mode, reset any 'running' instances
if c_remote_mode == 'True':
    query = {"acco.host": c_host_id, "acco.eventStatus": "running"}
    newvalues = {"$set": {"acco.eventStatus": "scheduled",
                          "acco.host": "", "acco.lastUpdate": ""}}
    for event in col_events.find(query):
        logging.warning(
            "Found instance in DB for this host flagged as 'running', de-allocating: " + str(event["acco"]))
    col_events.update_one(query, newvalues)

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

    # TODO: Look for instances with no running pid
    # TODO: check all instance pids

    # Look for events to start
    # If remote mode not selected, look for files in the ./events/ directory
    if (c_remote_mode) == 'False':
        for event_file in os.listdir("./events/"):
            if event_file.endswith(".json"):
                with open("./events/" + event_file) as serverconfig_file:
                    serverconfig = json.load(serverconfig_file)
                    # Call the event check and launch function
                    eventCheck(serverconfig)
    # If remote mode is selected, query mongo for scheduled events
    elif (c_remote_mode) == 'True':
        query = {"acco.eventStatus": "scheduled",
                 "acco.timeStart": {"$lt": time.time()}}
        for event in col_events.find(query):
            # print(event)
            eventconfig = json.dumps(
                event, sort_keys=True, indent=4, default=json_util.default)
            serverconfig = json.loads(eventconfig)
            # print(serverconfig["acco"])
            eventCheck(serverconfig)
        for event in col_events.find():
            print(event["acco"])
    else:
        logging.error(
            "Error finding events to start, remote mode flag not correctly set")

    # Wait to see if instances are available for the next step
    time.sleep(5)
    # If no scheduled events left and default lobbies configured, start Default settings on any available instances
    if (c_default_lobbies == "True"):
        for instance_num in instance_status:
            if (instance_status[instance_num]["status"] == "available"):
                logging.info(
                    "Instance slot available, starting default ")
                startInstance()

    # logging.info("Instance status: " + str(instance_status))

    # TODO: If remote mode, for each running instance check this is the right host and if not kill the instance
    # TODO: If remote mode, look for instances stuck on assigned
    time.sleep(5)
