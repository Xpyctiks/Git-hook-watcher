#!/usr/local/bin/python3

import os,logging,httpx,asyncio,json,glob,subprocess,shutil
from pathlib import Path

CONFIG_DIR = "/etc/git-hook-watcher/"
CONFIG_FILE = os.path.join(CONFIG_DIR,"git-hook-watcher.json")
TELEGRAM_TOKEN = TELEGRAM_CHATID = LOG_FILE = MARKER_DIR = WEB_ROOT = WEB_DATA_DIR = UID = GID = CHMODFOLDER = CHMODFILES = FILEMARKER_SUFFIX = SITE_PERSONAL_CONFIG = PRE_EXEC = POST_EXEC = ""

def load_config() -> None:
    """
    Check if config file exists. If not - generate the new one.
    """
    success = 0
    global TELEGRAM_TOKEN, TELEGRAM_CHATID, LOG_FILE, MARKER_DIR, WEB_ROOT, WEB_DATA_DIR, UID, GID, CHMODFOLDER, CHMODFILES, FILEMARKER_SUFFIX, SITE_PERSONAL_CONFIG, PRE_EXEC, POST_EXEC
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r',encoding='utf8') as file:
            config = json.load(file)
        for id,key in enumerate(config.keys()):
            if (key in ["logFile", "markerDir", "webRoot", "webDataDir", "uID", "gID", "chMODfolder", "chMODfiles", "fileMarkerSuffix", "sitePersonalConfigName", "pre-exec", "post-exec"]):
                if config.get(key) in [None, "", "None"]:
                    print(f"Important parameter of {key} is not defined! Can't proceed")
                    exit(1)
                else:
                    success += 1
        if success != 12:
            print(f"Some variables are not set in config file. Please fix it then run the program again.")
            exit(1)
        TELEGRAM_TOKEN = config.get('telegramToken').strip()
        TELEGRAM_CHATID = config.get('telegramChat').strip()
        LOG_FILE = config.get('logFile').strip()
        MARKER_DIR = config.get('markerDir').strip()
        WEB_ROOT = config.get('webRoot').strip()
        WEB_DATA_DIR = config.get('webDataDir').strip()
        UID = config.get('uID').strip()
        GID = config.get('gID').strip()
        CHMODFOLDER = config.get('chMODfolder').strip()
        CHMODFILES = config.get('chMODfiles').strip()
        FILEMARKER_SUFFIX = config.get('fileMarkerSuffix').strip()
        SITE_PERSONAL_CONFIG = config.get('sitePersonalConfigName').strip()
        PRE_EXEC = config.get('pre-exec').strip()
        POST_EXEC = config.get('post-exec').strip()
        logging.basicConfig(filename=LOG_FILE,level=logging.INFO,format='%(asctime)s - Git-Hook-Watcher - %(levelname)s - %(message)s',datefmt='%d-%m-%Y %H:%M:%S')
    else:
        generate_default_config()

def generate_default_config() -> None:
    """
    Checks every application loads if the app's configuration exists. If not - creates config file with default values
    """
    global TELEGRAM_TOKEN, TELEGRAM_CHATID, LOG_FILE, MARKER_DIR, WEB_ROOT, WEB_DATA_DIR, UID, GID, CHMODFOLDER, CHMODFILES, FILEMARKER_SUFFIX, SITE_PERSONAL_CONFIG, PRE_EXEC, POST_EXEC
    config =  {
        "telegramToken": "",
        "telegramChat": "",
        "logFile": "/var/log/git-hook-watcher.log",
        "markerDir": "./",
        "webRoot": "/var/www",
        "webDataDir": "data",
        "fileMarkerSuffix": "-start",
        "sitePersonalConfigName": ".git-hook-watcher",
        "uID": "*",
        "gID": "*",
        "chMODfolder": "770",
        "chMODfiles": "660",
        "pre-exec": "*",
        "post-exec": "*"
    }
    if not os.path.exists(CONFIG_DIR):
        os.mkdir(CONFIG_DIR)
    with open(CONFIG_FILE, 'w',encoding='utf8') as file:
        json.dump(config, file, indent=4)
    os.chmod(CONFIG_FILE, 0o600)
    print(f"First launch. New config file {CONFIG_FILE} generated and needs to be configured.")
    quit()

def check_running() -> None:
    """
    Before we proceed with main function - checks if there any other copy is still running
    """
    if os.path.exists("/var/run/git-hook-watcher.pid"):
        with open("/var/run/git-hook-watcher.pid", 'r',encoding='utf8') as file:
            PID = file.read()
        if os.path.exists(os.path.join("/proc/",PID)):
            print(f"Error! Another copy with PID={PID} is still running!")
            logging.error(f"Error! Another copy with PID={PID} is still running!")
            asyncio.run(send_to_telegram(f"Error! Another copy with PID={PID} is still running!"))
            exit(1)
        else:
            logging.info("Old PID file found from previous launch, which hasn't been removed")
            print("Old PID file found from previous launch, which hasn't been removed")

def finish_job() -> None:
    if os.path.exists("/var/run/git-hook-watcher.pid"):
        os.unlink("/var/run/git-hook-watcher.pid")
    logging.info("-----------------------------------------Git-hook-watcher script finished its work--------------------------------")

async def send_to_telegram(message: str, subject: str = os.uname().nodename+"["+os.path.splitext(os.path.basename(__file__))[0]+"]") -> None:
    """Sends messages via Telegram if TELEGRAM_CHATID and TELEGRAM_TOKEN are both set. Requires "message" parameters and can accept "subject" """
    if TELEGRAM_CHATID and TELEGRAM_TOKEN:
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "chat_id": f"{TELEGRAM_CHATID}",
            "text": f"{subject}\n{message}",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    headers=headers,
                    json=data
                )
            print(response.status_code)
            if response.status_code != 200:
                logging.error("error", f"Telegram bot error! Status: {response.status_code} Body: {response.text}")
        except Exception as err:
            logging.error(f"Error while sending message to Telegram: {err}")

def exec_script(script: str, domain: str, type: str) -> None:
    """
    Executes pre/post-script, defined in personal config file for domain. Full path to script required.Type is: pre-script or post-script.
    """
    if type == "pre-script":
        if PRE_EXEC == "-":#If "-" set in global config - disable any PRE scripts
            logging.info(f"{type}: execution of scripts is globally disabled...")
            return
        elif PRE_EXEC != "-" and PRE_EXEC != "*":
            logging.info(f"{type}: found globally enabled script {PRE_EXEC}")
            _SCRIPT = PRE_EXEC
        elif PRE_EXEC == "*":
            if script == "None":
                logging.info("No pre-script found for this domain.")
                return
            else:
                logging.info(f"Pre-script found for this domain: {script}")
                _SCRIPT = script
    if type == "post-script":
        if POST_EXEC == "-":#If "-" set in global config - disable any POST scripts
            logging.info(f"{type}: execution of scripts is globally disabled...")
            return
        elif POST_EXEC != "-" and POST_EXEC != "*":
            logging.info(f"{type}: found globally enabled script {POST_EXEC}")
            _SCRIPT = POST_EXEC
        elif POST_EXEC == "*":
            if script == "None":
                logging.info("No post-script found for this domain.")
                return
            else:
                logging.info(f"Post-script found for this domain: {script}")
                _SCRIPT = script
    """Main function"""
    if os.path.exists(_SCRIPT):
        result = subprocess.run(_SCRIPT, capture_output=True, text=True, shell=True)
        logging.info(str(result))
        if result.returncode == 0:
            logging.info(f"{type} {_SCRIPT} for domain {domain} finished. Starting pull...")
        else:
            logging.error(f"{type} {_SCRIPT} for domain {domain} finished with error!")
            asyncio.run(send_to_telegram(f"⚠{type} {_SCRIPT} for domain {domain} finished with error."))
    else:
        logging.error(f"{type} {_SCRIPT} for domain {domain} is not exists!")
        asyncio.run(send_to_telegram(f"⚠{type} {_SCRIPT} for domain {domain} is not exists!"))

def purge_cache(cache_path: str) -> None:
    """
    Purge nginx cache in given folder
    """
    if len(cache_path) > 4:#additional check if the received path is not too short to be like "/" or "./"
        if os.path.exists(cache_path):
            os.chdir(cache_path)
            CURRENT_DIR = os.getcwd()
            if CURRENT_DIR != cache_path:
                logging.error(f"Purge_cache(): Error: current folder {CURRENT_DIR} is not equal to cache dir: {cache_path}")
                asyncio.run(send_to_telegram(f"⚠Purge_cache(): Error: current folder {CURRENT_DIR} is not equal to cache dir: {cache_path}"))
                return
            for item in os.listdir(CURRENT_DIR):
                item_path = os.path.join(CURRENT_DIR, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as msg:
                    logging.error(f"Purge_cache(): Error deleting {cache_path}: {msg}")
                    asyncio.run(send_to_telegram(f"⚠Purge_cache(): Error deleting {cache_path}: {msg}"))
            logging.info(f"Purge_cache(): Cache in {cache_path} purged successfully")
        else:
            logging.error(f"Purge_cache(): Error deleting {cache_path}")
            asyncio.run(send_to_telegram(f"⚠Purge_cache(): Error deleting {cache_path}"))

def set_rights(data_folder: str, dir_rights: str, file_rights: str) -> None:
    """
    Sets rights for files and folders after pull is completed.Requires:\n
    dir_rights - default "770". "-" means don't change dir_rights\n
    file_rights - default "660". "-" means don't change file_rights
    """
    if dir_rights == "None" and CHMODFOLDER != "-" and CHMODFOLDER != "*": #If we haven't received dir_rights from additional config and globally they are not disabled - set as the global value says
        _DIR_RIGHTS = CHMODFOLDER
        logging.info(f"Set_rights(DIR): Got None from additional config and some value from global config - using {_DIR_RIGHTS}")
    elif dir_rights == "None" and CHMODFOLDER == "-": #If we haven't received dir_rights from additional config and global config says it is "-" - disabling set of the folder's rights
        _DIR_RIGHTS = "None"
        logging.info(f"Set_rights(DIR): Got None from additional config and \"-\" from global config - disabling set of folder's rights")
    elif dir_rights == "None" and CHMODFOLDER == "*": #If we haven't received dir_rights from additional config and global config says it is "*" - set rights according to domain's root folder.
        _DIR_RIGHTS = oct(os.stat(os.getcwd()).st_mode)[-3:]
        logging.info(f"Set_rights(DIR): Got None from additional config and \"*\" from global - set rights to {_DIR_RIGHTS} from domain's root folder.")
    elif dir_rights != "None" and dir_rights != "*" and dir_rights != "-": #If we have received dir_rights from additional config and they are not "-" or "*" - set it to the given value
        _DIR_RIGHTS = dir_rights
        logging.info(f"Set_rights(DIR): Got {_DIR_RIGHTS} from additional config.")
    elif dir_rights != "None" and dir_rights == "*": #If we have received dir_rights from additional config and they are "*" - set rights according to domain's root folder.
        _DIR_RIGHTS = oct(os.stat(os.getcwd()).st_mode)[-3:]
        logging.info(f"Set_rights(DIR): Got \"*\" from additional config - set rights to {_DIR_RIGHTS} from domain's root folder.")
    elif dir_rights != "None" and dir_rights == "-": #If we have received dir_rights from additional config and they are "-" - disabling set of rights
        _DIR_RIGHTS = "None"
        logging.info(f"Set_rights(DIR): Got \"-\" from additional config - disabling set of rights.")
    """File mode section"""
    if file_rights == "None" and CHMODFILES != "-": #If we haven't received file_rights from additional config and globally they are not disabled - set as the global value says
        _FILES_RIGHTS = CHMODFILES
        logging.info(f"Set_rights(FILE): Got None from additional config and some value from global config - using {_FILES_RIGHTS}")
    elif file_rights == "None" and CHMODFILES == "-": #If we haven't received file_rights from additional config and global config says it is "-" - disabling set of the files rights
        _FILES_RIGHTS = "None"
        logging.info(f"Set_rights(FILE): Got None from additional config and \"-\" from global config - disabling set of folder's rights")
    elif file_rights != "None" and file_rights != "-": #If we have received files_rights from additional config and they are not "-" - set it to the given value
        _FILES_RIGHTS = file_rights
        logging.info(f"Set_rights(FILE): Got {_FILES_RIGHTS} from additional config.")
    elif file_rights != "None" and file_rights == "-": #If we have received files_rights from additional config and they are "-" - disabling set of rights
        _FILES_RIGHTS = "None"
        logging.info(f"Set_rights(FILE): Got \"-\" from additional config - disabling set of rights.")
    """Set all rights now"""
    if os.getcwd() == data_folder:
        if _DIR_RIGHTS != "None":
            logging.info(f"Starting set dir_rights to {_DIR_RIGHTS}")
            result = subprocess.run("find -type d -exec chmod " + _DIR_RIGHTS + " '{}' ';'", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info("Set of dir_rights completed!")
            else:
                logging.error("Set of dir_rights failed!")
                asyncio.run(send_to_telegram(f"⚠Set_rights(): set of dir_rights failed!"))
        if _FILES_RIGHTS != "None":
            logging.info(f"Starting set file_rights to {_FILES_RIGHTS}")
            result = subprocess.run("find -type f -exec chmod " + _FILES_RIGHTS + " '{}' ';'", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info("Set of file_rights completed!")
            else:
                logging.error("Set of file_rights failed!")
                asyncio.run(send_to_telegram(f"⚠Set_rights(): set of file_rights failed!"))
    else:
        logging.error(f"Set_owner(): set UID and GID failed because we are not in expected dir. - {data_folder}. We are in {os.getcwd()}")
        asyncio.run(send_to_telegram(f"⚠Set_owner(): set UID and GID failed because we are not in expected dir. - {data_folder}. We are in {os.getcwd()}"))

def set_owner(data_folder: str, uid: str, gid: str, dir_rights: str, file_rights: str) -> None:
    """
    Sets UID and GID for files and folders and do chmod for them after pull is completed.Requires:\n
    uid - default "*" which means user is as the user of root domain folder. "-" means don't change user\n
    gid - default "*" which means group is as the user of root domain folder. "-" means don't change group\n
    dir_rights - default "770". "-" means don't change dir_rights\n
    file_rights - default "660". "-" means don't change file_rights
    """
    if uid == "None" and UID == "*": #If we haven't received uid from additional config and global config says it is "*" now - set as the root folder's owner
        _UID = os.stat(os.getcwd()).st_uid
        logging.info(f"Set_owner(UID): Got None from additional config and \"*\" from global config - using root folder's owner as user: {_UID}")
    elif uid == "None" and UID == "-": #If we haven't received uid from additional config and global config says it is "-" now - disables set of the folder's owner
        _UID = "None"
        logging.info(f"Set_owner(UID): Got None from additional config and \"-\" from global config - disabling set of folder's owner")
    elif uid == "None" and UID != "-" and UID != "*": #If we haven't received uid from additional config and global config has some value - set owner to this value
        _UID = UID
        logging.info(f"Set_owner(UID): Got None from additional config and {_UID} from global config - set it as folder's owner")
    elif uid != "None" and uid != "-" and uid != "*":#If we have received uid from additional config and and it is not "-" - set the root folder's owner.
        _UID = uid
        logging.info(f"Set_owner(UID): Got UID {_UID} from additional config - using it as user")
    elif uid == "-":#If we have received uid from additional config and it is "-" - disable to set folder's owner.
        _UID = "None"
        logging.info(f"Set_owner(UID): Got \"-\" from additional config - disabling set of folder's owner")
    elif uid == "*":#If we have received uid from additional config and it is "*" - set as the root folder's owner.
        _UID = os.stat(os.getcwd()).st_uid
        logging.info(f"Set_owner(UID): Got \"*\" from additional config - set of folder's owner {_UID}")
    """GID set"""
    if gid == "None" and GID == "*": #If we haven't received gid from additional config and global config says it is "*" now - set as the root folder's group
        _GID = os.stat(os.getcwd()).st_gid
        logging.info(f"Set_owner(GID): Got None from additional config and \"*\" from global config - using root folder's group as group: {_GID}")
    elif gid == "None" and GID == "-": #If we haven't received gid from additional config and global config says it is "-" now - disables set of the folder's group
        _GID = "None"
        logging.info(f"Set_owner(GID): Got None from additional config and \"-\" from global config - disabling set of folder's group")
    elif gid == "None" and GID != "-" and GID != "*": #If we haven't received gid from additional config and global config has some value - set group to this value
        _GID = GID
        logging.info(f"Set_owner(GID): Got None from additional config and {_GID} from global config - set it as folder's group")
    elif gid != "None" and gid != "-" and gid != "*":#If we have received gid from additional config and and it is not "-" - set the root folder's group.
        _GID = gid
        logging.info(f"Set_owner(GID): Got GID {_GID} from additional config - using it as group")
    elif gid == "-":#If we have received uid from additional config and it is "-" - disable to set folder's owner.
        _GID = "None"
        logging.info(f"Set_owner(GID): Got \"-\" from additional config - disabling set of folder's owner")
    elif gid == "*":#If we have received uid from additional config and it is "*" - set as the root folder's owner.
        _GID = os.stat(os.getcwd()).st_gid
        logging.info(f"Set_owner(GID): Got \"*\" from additional config - set of folder's owner {_GID}")
    """Set UID and GID now"""
    if os.getcwd() == data_folder:
        if _UID != "None" and _GID != "None":
            logging.info(f"Starting set UID {_UID} and GID {_GID}:")
            result = subprocess.run(f"chown -R {_UID}:{_GID} *", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info("Set UID and GID completed!")
            else:
                logging.error("Set UID and GID failed!")
                asyncio.run(send_to_telegram(f"⚠Set_owner(): set UID and GID failed!"))
        elif _UID != "None" and _GID == "None":
            logging.info(f"Starting set UID {_UID} only:")
            result = subprocess.run(f"chown -R {_UID} *", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info("Set of UID completed!")
            else:
                logging.error("Set of UID failed!")
                asyncio.run(send_to_telegram(f"⚠Set_owner(): set of UID failed!"))
        elif _UID == "None" and _GID != "None":
            logging.info(f"Starting set GID {_GID} only:")
            result = subprocess.run(f"chown -R :{_GID} *", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info("Set of GID completed!")
            else:
                logging.error("Set of GID failed!")
                asyncio.run(send_to_telegram(f"⚠Set_owner(): set of GID failed!"))
    else:
        logging.error(f"Set_owner(): set UID and GID failed because we are not in expected dir. - {data_folder}. We are in {os.getcwd()}")
        asyncio.run(send_to_telegram(f"⚠Set_owner(): set UID and GID failed because we are not in expected dir. - {data_folder}. We are in {os.getcwd()}"))
    set_rights(data_folder, dir_rights, file_rights)

def del_marker(domain: str) -> None:
    """
    Little function deletes file marker to prevent loop launch of the script if any error occurs
    """
    try:
        os.chdir(Path(__file__).resolve().parent)
        os.unlink(os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX))
        logging.info(f"File-marker {os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX)} deleted successfully")
    except Exception as msg:
        logging.error(f"File-marker deletion error: {os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX)} was not deleted")
        asyncio.run(send_to_telegram(f"⚠File-marker deletion error: {os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX)} was not deleted"))

def main() -> None:
    """
    Main function which makes pull from repo. and does a few additional steps
    """
    os.chdir(Path(__file__).resolve().parent)
    PULL_LIST = glob.glob("*"+FILEMARKER_SUFFIX)
    if len(PULL_LIST) == 0:#if the script is launched, but no marker found - just silently quit
        exit(0)
    check_running()
    with open("/var/run/git-hook-watcher.pid", 'w',encoding='utf8') as file:
        file.write(str(os.getpid()))
    for i in range(len(PULL_LIST)):
        PULL_LIST[i] = PULL_LIST[i].replace(FILEMARKER_SUFFIX, "")
    logging.info(f"List of domains for pull: {PULL_LIST}")
    logging.info("-----------------------------------------Starting git-hook-watcher script-----------------------------------------")
    for domain in PULL_LIST:
        logging.info(f">>>>>>> Starting domain {domain}")
        asyncio.run(send_to_telegram(f"👀Starting pull job for domain {domain}"))
        logging.info(f"Heading to dir. {os.path.join(WEB_ROOT,domain)} for additional config file for Git-hook-watcher {os.path.join(WEB_ROOT,domain,SITE_PERSONAL_CONFIG)}")
        """Generating full path to a website main folder with the personal config file name"""
        PERSONAL_CONFIG_FILE = os.path.join(WEB_ROOT,domain,SITE_PERSONAL_CONFIG)
        VALUES_LIST = []
        REDIRECTS_LIST = []
        if os.path.exists(PERSONAL_CONFIG_FILE):
            logging.info(f"Additional config found for {domain}")
            """Loading all from the config file"""
            with open(PERSONAL_CONFIG_FILE, 'r',encoding='utf8') as file:
                PERSONAL_CONFIG = json.load(file)
                """Parsing the file for any valid value in there"""
                for key in PERSONAL_CONFIG:
                    if key == "pre-exec":
                        EXEC_PRE_SCRIPT = PERSONAL_CONFIG.get('pre-exec').strip()
                        VALUES_LIST.append("pre-exec")
                    elif key == "post-exec":
                        EXEC_POST_SCRIPT = PERSONAL_CONFIG.get('post-exec').strip()
                        VALUES_LIST.append("post-exec")
                    elif key == "uid":
                        _UID = PERSONAL_CONFIG.get('uid').strip()
                        VALUES_LIST.append("uid")
                    elif key == "gid":
                        _GID = PERSONAL_CONFIG.get('gid').strip()
                        VALUES_LIST.append("gid")
                    elif key == "dir_rights":
                        DIR_RIGHTS = PERSONAL_CONFIG.get('dir_rights').strip()
                        VALUES_LIST.append("dir_rights")
                    elif key == "file_rights":
                        FILE_RIGHTS = PERSONAL_CONFIG.get('file_rights').strip()
                        VALUES_LIST.append("file_rights")
                    elif key == "redirects":
                        REDIRECTS_LIST = PERSONAL_CONFIG.get('redirects',[])
                        VALUES_LIST.append("redirects")
                    elif key == "cachePath":
                        CACHE_PATH = PERSONAL_CONFIG.get('cachePath')
                        VALUES_LIST.append("cachePath")
            logging.info(f"Values we got from additional config: {VALUES_LIST}")
        else:
            logging.info(f"No additional config found for {domain}")
        """Getting requested branch name from marker file to make futher decision - shoud it be working branch or redirected one"""
        try:
            with open(os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX), 'r',encoding='utf8') as file:
                COMMIT_ID, DOMAIN, REQUESTED_BRANCH = file.read().split(" ",3)
                REQUESTED_BRANCH = REQUESTED_BRANCH.split('/',3)[2]
        except Exception as msg:
            logging.error(f"Error exception while reading marker file {os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX)}! {msg}")
            asyncio.run(send_to_telegram(f"⚠Error reading marker file {os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX)}! {msg}"))
            del_marker(domain)
            continue
        logging.info(f"Got data from the marker file {os.path.join(MARKER_DIR,domain+FILEMARKER_SUFFIX)}: COMMIT_ID:{COMMIT_ID}, DOMAIN:{DOMAIN}, REQUESTED_BRANCH:{REQUESTED_BRANCH}, REDIRECTS_LIST:{REDIRECTS_LIST}")
        """Making decision - do we make redirect or not"""
        if any(REQUESTED_BRANCH in branch for branch in REDIRECTS_LIST):
            """If there is redirect"""
            logging.info(f"Found redirect: Branch: {REQUESTED_BRANCH}, New path: {REDIRECTS_LIST[0][REQUESTED_BRANCH]}")
            """check if redirection folder actually exists. If not, alert + skip"""
            if not os.path.exists(REDIRECTS_LIST[0][REQUESTED_BRANCH]):
                logging.error(f"Redirection path {REDIRECTS_LIST[0][REQUESTED_BRANCH]}, which is set for branch {REQUESTED_BRANCH}, is not exists! Skipping this domain...")
                asyncio.run(send_to_telegram(f"🚨Redirection path \"{REDIRECTS_LIST[0][REQUESTED_BRANCH]}\", which is set for branch \"{REQUESTED_BRANCH}\", is not exists!"))
                del_marker(domain)
                continue
            """If everything is ok - heading to the folder"""
            os.chdir(REDIRECTS_LIST[0][REQUESTED_BRANCH])
            if "EXEC_PRE_SCRIPT" in locals(): #if there is set pre-exec script for current domain - execute it before all other steps
                exec_script(EXEC_PRE_SCRIPT, domain, "pre-script")
            else:
                exec_script("None", domain, "pre-script")
            result = subprocess.run("git pull", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info(f"Pull with redirect completed! Domain: {domain}, Redirect to: {REDIRECTS_LIST[0][REQUESTED_BRANCH]}, Branch: {REQUESTED_BRANCH}, CommitID: {COMMIT_ID}")
                if not "_UID" in locals():
                    _UID = "None"
                if not "_GID" in locals():
                    _GID = "None"
                if not "DIR_RIGHTS" in locals():
                    DIR_RIGHTS = "None"
                if not "FILE_RIGHTS" in locals():
                    FILE_RIGHTS = "None"
                set_owner(os.path.join(WEB_ROOT,domain,WEB_DATA_DIR), _UID, _GID, DIR_RIGHTS, FILE_RIGHTS)
                if "CACHE_PATH" in locals():
                    purge_cache(CACHE_PATH)
                if "EXEC_POST_SCRIPT" in locals(): #if there is set post-exec script for current domain - execute it after all steps are finished
                    exec_script(EXEC_POST_SCRIPT, domain, "post-script")
                else:
                    exec_script("None", domain, "post-script")
                asyncio.run(send_to_telegram(f"✅Pull with redirect completed!\nDomain: {domain}\nRedirect to: {REDIRECTS_LIST[0][REQUESTED_BRANCH]}\nBranch: {REQUESTED_BRANCH}\nCommitID: {COMMIT_ID}"))
            else:
                logging.error(f"Pull with redirect error! Domain: {domain}, Redirect to: {REDIRECTS_LIST[0][REQUESTED_BRANCH]}, Branch: {REQUESTED_BRANCH}, CommitID: {COMMIT_ID}")
                asyncio.run(send_to_telegram(f"🚨Pull with redirect error!\nDomain: {domain}, Redirect to: {REDIRECTS_LIST[0][REQUESTED_BRANCH]}, Branch: {REQUESTED_BRANCH}, CommitID: {COMMIT_ID}\n{result.stderr}"))
        else:
            """If there is NO redirect"""
            logging.info(f"Requested branch {REQUESTED_BRANCH} is not found in redirects list.Making direct pull with this branch.")
            """check if the folder actually exists. If not, alert + skip"""
            if not os.path.exists(os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)):
                logging.error(f"Path {os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)}, which is set for branch {REQUESTED_BRANCH}, is not exists! Skipping this domain...")
                asyncio.run(send_to_telegram(f"🚨Path {os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)}, which is set for branch {REQUESTED_BRANCH}, is not exists! Skipping this domain..."))
                del_marker(domain)
                continue
            """If everything is ok - heading to the folder"""
            os.chdir(os.path.join(WEB_ROOT,domain,WEB_DATA_DIR))
            if "EXEC_PRE_SCRIPT" in locals(): #if there is set pre-exec script for current domain - execute it before all other steps
                exec_script(EXEC_PRE_SCRIPT, domain, "pre-script")
            else:
                exec_script("None", domain, "pre-script")
            result = subprocess.run("git pull", capture_output=True, text=True, shell=True)
            logging.info(str(result))
            if result.returncode == 0:
                logging.info(f"Pull completed! Domain: {domain}, Path: {os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)}, Branch: {REQUESTED_BRANCH}, CommitID: {COMMIT_ID}")
                if not "_UID" in locals():
                    _UID = "None"
                if not "_GID" in locals():
                    _GID = "None"
                if not "DIR_RIGHTS" in locals():
                    DIR_RIGHTS = "None"
                if not "FILE_RIGHTS" in locals():
                    FILE_RIGHTS = "None"
                set_owner(os.path.join(WEB_ROOT,domain,WEB_DATA_DIR), _UID, _GID, DIR_RIGHTS, FILE_RIGHTS)
                if "CACHE_PATH" in locals():
                    purge_cache(CACHE_PATH)
                if "EXEC_POST_SCRIPT" in locals(): #if there is set post-exec script for current domain - execute it after all steps are finished
                    exec_script(EXEC_POST_SCRIPT, domain, "post-script")
                else:
                    exec_script("None", domain, "post-script")
                asyncio.run(send_to_telegram(f"✅Pull completed!\nDomain: {domain}\nPath: {os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)}\nBranch: {REQUESTED_BRANCH}\nCommitID: {COMMIT_ID}"))
            else:
                logging.error(f"Pull error! Domain: {domain}, Path: {os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)}, Branch: {REQUESTED_BRANCH}, CommitID: {COMMIT_ID}")
                asyncio.run(send_to_telegram(f"🚨Pull error!\nDomain: {domain}, Path: {os.path.join(WEB_ROOT,domain,WEB_DATA_DIR)}, Branch: {REQUESTED_BRANCH}, CommitID: {COMMIT_ID}\n{result.stderr}"))
        del_marker(domain)
        logging.info(f">>>>>>> Finished domain {domain}")

if __name__ == "__main__":
    load_config()
    main()
    finish_job()
