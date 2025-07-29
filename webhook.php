<?php
//getting variables from config file
$confFile="./webhook.conf";
if (file_exists($confFile)) {
  include $confFile;
  if (empty($gogsHookPsk) || empty($markerPath))
  {
    error_log("ERROR: Some important variables are not set in the config file not found. Interrupting...",0);
    echo("ERROR: Some important variables are not set in the config file not found. Interrupting...");
    die();
  }
} else {
  error_log("ERROR: Config file not found. Creating the new one and interrupting.",0);
  echo("ERROR: Config file not found. Creating the new one and interrupting.");
  $config='<?php
//This is PSK for Gogs webhook,needed for validation of requests from outside
$gogsHookPsk="123Passw0rd123";
//API token for Telegram. Leave empty if dont want to receive Telegram notifications.
$apiToken="";
$chatId="";
//Path where to create marker file, with trailing slash
$markerPath="./";
//For usage with telegrambot.php. API token to allow access.If not set,all other tgBot parameters are ignored.
$tgBotApiToken="";
//For usage with telegrambot.php. Where the main Web folder is located.
$tgBotWwwFolder="";';
  file_put_contents($confFile,$config);
  die();
}
global $dataArr;

$data = file_get_contents('php://input');
$data = json_decode($data, true);

//Verification function.All requests from Gogs are being validated using PSK defined in Gogs and here above.
function verify_webhook($data, $hmac_header)
{
  global $gogsHookPsk;
  $result=false;
  $calculated_hmac = hash_hmac('sha256', $data, $gogsHookPsk, false);
  if ($hmac_header == $calculated_hmac) { $result=true; }
  return $result;
}

//--------------------------------------------------Here we create functions named as the action item on telegrambot.conf Actions array-------------------------------------------------------
function MakePull() {
  global $data,$tgBotServersArray,$apiToken,$chatId,$site,$markerPath;
  $serverName=file_get_contents("/etc/hostname");
  file_put_contents($markerPath.$site."-start","DevOps-Bot-request-by-".$_POST['from']);
  if (!empty($apiToken) && !empty($chatId)) {
    $data = [
      'chat_id' => "$chatId",
      'text' => "☸ New pull request via DevOps Bot!\nRequester: ".$_POST['from']."\nSite: ".$site."\nServer: ".$serverName,
    ];
    file_get_contents("https://api.telegram.org/bot$apiToken/sendMessage?".http_build_query($data));
  }
  die();
}

function GitStash() {
  global $data,$tgBotServersArray,$apiToken,$chatId,$site,$markerPath;
  $serverName=file_get_contents("/etc/hostname");
  file_put_contents($markerPath.$site."-stash","DevOps-Bot-request-by-".$_POST['from']);
  if (!empty($apiToken) && !empty($chatId)) {
    $data = [
      'chat_id' => "$chatId",
      'text' => "☸ Git Stash request via DevOps Bot!\nRequester: ".$_POST['from']."\nSite: ".$site."\nServer: ".$serverName,
    ];
    file_get_contents("https://api.telegram.org/bot$apiToken/sendMessage?".http_build_query($data));
  }
  die();
}
//--------------------------------------------------End of actions functions-------------------------------------------------------------------------------------------------------------------

if (isset($_GET['notify']))
{
  $hmac_header = $_SERVER['HTTP_X_GOGS_SIGNATURE'];
  $data = file_get_contents('php://input');
  $verified = verify_webhook($data, $hmac_header);
  $dataArr = json_decode($data,true);
  echo("General push notification received.\nVerified: ".$verified."\nServer event: ".$_SERVER['HTTP_X_GOGS_EVENT']."\nRef: ".$dataArr["ref"]);
  if (($_SERVER['HTTP_X_GOGS_EVENT'] == "push")) {
    if (!empty($apiToken) && !empty($chatId)) {
      $data = [
        'chat_id' => "$chatId",
        'text' => "☄ General push to Git (not main sites).\nRepository: ".$dataArr["repository"]["name"]."\nOrganization: ".$dataArr["repository"]["owner"]["username"]."\nBranch: ".$dataArr["ref"]."\nPusher: ".$dataArr["pusher"]["username"]."\nID: ".$dataArr["commits"][0]["id"]."\nComment: ".$dataArr["commits"][0]["message"],
      ];
      file_get_contents("https://api.telegram.org/bot$apiToken/sendMessage?".http_build_query($data));
    }
  }
  die();
}

//check if tgBotApiToken is set to make all other functions active
if (isset($_POST['tgBotCall']) && empty($tgBotApiToken)) {
  echo("Error! tgBotApiToken is not set.That means all tgBot functions are disabled!");
  die();
}
elseif (isset($_POST['tgBotCall']) && !empty($tgBotApiToken)) {
  if (empty($tgBotWwwFolder)) {
    echo("Error! Some of tgBot variables is not set.That means all tgBot functions are disabled!");
    die();
  }
}
//main function to work with remote API calls from telegrambot.php
if (isset($_POST['tgBotCall']) && ($tgBotApiToken == $_POST['tgBotApiToken'])) {
  switch ($_POST['tgBotCall']) 
  {
    case "listSites":
      $fp=popen("ls ".$tgBotWwwFolder,"r");
      while ($rec=fgets($fp)) {
        $dataArray[] = trim($rec);
      }
      $domains=array();
      $domains=json_encode($dataArray);
      echo($domains);
      exit();
    case "makeAction":
      $action=$_POST['action'];
      $site=$_POST['site'];
      if (!empty($action) && !empty($site)) {
        call_user_func($action,"");
      }
      $domains=array();
      $domains=json_encode($dataArray);
      echo($domains);
      exit();
  }
}

if ((isset($_SERVER['HTTP_X_GOGS_SIGNATURE'])) and (isset($_SERVER['HTTP_X_GOGS_EVENT']))) 
{
  $hmac_header = $_SERVER['HTTP_X_GOGS_SIGNATURE'];
  $data = file_get_contents('php://input');
  $verified = verify_webhook($data, $hmac_header);
  $dataArr = json_decode($data,true);
  $serverName=file_get_contents("/etc/hostname");
  //Send info about received push as an answer to Gog. Usefull to check hooks logs in Gogs
  echo("Push received.\nVerified: ".$verified."\nServer event: ".$_SERVER['HTTP_X_GOGS_EVENT']."\nRef: ".$dataArr["ref"]);
  if (($verified) and ($_SERVER['HTTP_X_GOGS_EVENT'] == "push")) {
    file_put_contents($markerPath.$dataArr["repository"]["name"]."-start",$dataArr["commits"][0]["id"]." ".$dataArr["repository"]["name"]." ".$dataArr["ref"]);
    if (!empty($apiToken) && !empty($chatId)) {
      $data = [
        'chat_id' => "$chatId",
        'text' => "📫 New push to Git!\nRepository: ".$dataArr["repository"]["name"]."\nOrganization: ".$dataArr["repository"]["owner"]["username"]."\nBranch: ".$dataArr["ref"]."\nPusher: ".$dataArr["pusher"]["username"]."\nID: ".$dataArr["commits"][0]["id"]."\nComment: ".$dataArr["commits"][0]["message"]."Server: ".$serverName,
      ];
      file_get_contents("https://api.telegram.org/bot$apiToken/sendMessage?".http_build_query($data));
    }
  } elseif (!($verified) and ($_SERVER['HTTP_X_GOGS_EVENT'] == "push")) {
    //Send info about received push as an answer to Gog. Usefull to check hooks logs in Gogs
    echo("Push received.\nVerified: FALSE\nServer event: ".$_SERVER['HTTP_X_GOGS_EVENT']."\nRef: ".$dataArr["ref"]);
    if (!empty($apiToken) && !empty($chatId)) {
      $data = [
        'chat_id' => "$chatId",
        'text' => "🔍Error! New push received, but wrong or absent HMAC auth key!\nRepository: ".$dataArr["repository"]["name"]."\nOrganization: ".$dataArr["repository"]["owner"]["username"]."\nBranch: ".$dataArr["ref"]."\nPusher: ".$dataArr["pusher"]["username"]."\nID: ".$dataArr["commits"][0]["id"]."\nComment: ".$dataArr["commits"][0]["message"]."Server: ".$serverName,
      ];
      file_get_contents("https://api.telegram.org/bot$apiToken/sendMessage?".http_build_query($data));
    }
  }
}
else
{
	echo("Try to guess...\n");
}
?>
