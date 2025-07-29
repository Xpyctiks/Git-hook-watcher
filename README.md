## Git-hook-watcher  
  
This is a combination of two scripts:  
1. PHP script which serves external API call from your GOGs or other app. The script creates a file-marker inside the marker directory, which is set inside config file.  
   File marker's name contains domain name + "-start" suffix. Inside it stores commit_id, domain and branch.  
2. Main Python script. This script should be called by CRON. When being launched, it checks the markerDir (set in config.) for marker files, and if found - the script starts actions:  
   - Checks if the destination directory exists, then head into and trys to locate additional personal configuration file .git-hook-watcher inside the directory. When found, all settings from the config have higher priority then settings from general config.  
   - Checks requested branch from marker file - is that branch in REDRIECTS section of personal config? If yes - doing redirect to another path from the config file. If the requested branch is not redirected - heads inside web site's working folder and does "git pull" command.  
   - If in personal config file any of "pre-exec" and "post-exec" script is set - this script is being launched before or after all actions.  
   - If "cachePath" in additional config. only is set - after pull it will purge all files and folders inside cache folder.Usefull for nginx cache.  

### Global settings:  

Global settings are in automatically generated config file, which is at /etc/git-hook-watcher/ folder. The settings are:  
   - "telegramToken" and "telegramChat" - settings for Telegram bot. Allows to receive all messages.  
   - "logfile" - full path to the log file  
   - "markerDir" - a directory, where webhook.php creates file-markers and where Python script os looking for them.  
   - "webRoot" - general web root, where all sites are stored. This folder will be checked for any domain from file-marker.  
   - "webDataDir" - main working directory inside the site folder, where all public scripts are stored.Git will try to make pull in this folder of any site.  
   - "fileMarkerSuffix" - suffix for marker-file. Now it is "domain-name"-start. Here "-start" is that suffix which is being added to all domain names of the marker file.  
   - "sitePersonalConfigName" - the name of file, which can be stored in site's root folder and its additional settings will be applied every pull  
   - "uID" - you can set "-" to globally disable setting of uid. Value "*" means to set uid according the site's root folder user.  
   - "gID" - you can set "-" to globally disable setting of gid. Value "*" means to set gid according the site's root folder group.  
   - "chMODfolder" - you can set "-" to globally disable chmod of directories inside the site's data folder. Value "*" means to set directory rights according the site's data folder rights. Or globally rights can be set.
   - "chMODfiles"  - you can set "-" to globally disable chmod of directories inside the site's data folder. Or globally rights can be set.   
   - "pre-exec" and "post-exec" - full path to scripts which will be executed before and after actions. Can be set globally for all - if set script path. Can be globally disbled if value is "-". Can be turned on - value "*", but should be personally set from additional config from every site's folder.  

### Additional config file .git-hook-watcher:  

An example of all possible options inside the file.  
Sure thing, only necessary values can be inside the file. Don't need to keep all that text inside.  All values are useing default values or are being ignored if they are not overriden here, in additional config file. Values from this file have higher priority then global.  
```
{
    "pre-exec": "/usr/local/bin/pre.sh",
    "post-exec": "/usr/local/bin/post.sh",
    "uid": "*",
    "gid": "*",
    "dir_rights": "777",
    "file_rights": "666",
    "redirects": [
        {
            "development": "/var/www/dev.site2.com",
            "testing": "/var/www/test.site2.com"
        }
    ]
}
```
