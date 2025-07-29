<?php
//getting variables from config file
$confFile="./telegrambot.conf";
if (file_exists($confFile)) {
  include $confFile;
  if (empty($apiToken) || empty($chatId) || empty($tgBotApiToken))
  {
    error_log("ERROR: Some important variables are not set in the config file not found. Interrupting...",0);
    echo("ERROR: Some important variables are not set in the config file not found. Interrupting...");
    die();
  }
} else {
  error_log("ERROR: Config file not found. Creating the new one and interrupting.",0);
  echo("ERROR: Config file not found. Creating the new one and interrupting.");
  $config='<?php
//API token for Telegram. Leave empty if dont want to receive Telegram notifications.
$apiToken="";
$chatId="";
//Array of branches to react by webhook
//For usage with telegrambot.php. API token to allow access.If not set,all other tgBot parameters are ignored.
$tgBotApiToken="";
//For usage with telegrambot.php.An array of available actions.
$tgBotActionsArray=array("Action1", "Action2");
//For usage with telegrambot.php.An array of available servers.
$tgBotServersArray=array("Server1", "Server2");';
  file_put_contents($confFile,$config);
  die();
}

$arrayServers=array();
$arrayActions=array();
$arraySites=array();

//general functions to send messages to Telegram
function sendTelegram($method, $response)
{
  global $apiToken;
  $ch = curl_init('https://api.telegram.org/bot'.$apiToken.'/'.$method);  
  curl_setopt($ch, CURLOPT_POST, 1);  
  curl_setopt($ch, CURLOPT_POSTFIELDS, $response);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  curl_setopt($ch, CURLOPT_HEADER, false);
  $res = curl_exec($ch);
  file_put_contents(__DIR__ . '/curl.txt', $res);
  curl_close($ch);
  return $res;
}

$data = file_get_contents('php://input');
$data = json_decode($data, true);

//--------------------------------------------------Here we create functions named as the action item on telegrambot.conf Actions array-------------------------------------------------------
function MakePull($actId) {
  global $data,$tgBotServersArray,$tgBotApiToken,$workingSite,$chatId,$tgBotActionsArray;
  //Making POST request to webhook.php with our action
  $opts = array(
    'http'=>array(
      'method'=>"POST",
      'header'=>"Content-Type: application/x-www-form-urlencoded\r\n".
                "User-Agent:XpyctTelegramBot/1.0",
      'content'=>"tgBotCall=makeAction&action=".$tgBotActionsArray[$actId[0]]."&site=".$workingSite."&from=".$data['callback_query']['from']['username']."&tgBotApiToken=".$tgBotApiToken
    ),
    "ssl"=>array(
      "verify_peer"=>false,
      "verify_peer_name"=>false,
    )
  );
  $context=stream_context_create($opts);
  $addrEnd=strpos($data['callback_query']['data'],"act-");
  $srvId=substr($data['callback_query']['data'],4,($addrEnd-5));
  $file=file_get_contents('https://'.$tgBotServersArray[$srvId].'/webhook.php', true, $context);
  sendTelegram('sendMessage', 
    array(
      'chat_id' => $chatId,
      'text' => '✅Pull trigger successfully sent!'
    ));
  die();
}

function GitStash($actId) {
  global $data,$tgBotServersArray,$tgBotApiToken,$workingSite,$chatId,$tgBotActionsArray;
  //Making POST request to webhook.php with our action
  $opts = array(
    'http'=>array(
      'method'=>"POST",
      'header'=>"Content-Type: application/x-www-form-urlencoded\r\n".
                "User-Agent:XpyctTelegramBot/1.0",
      'content'=>"tgBotCall=makeAction&action=".$tgBotActionsArray[$actId[0]]."&site=".$workingSite."&from=".$data['callback_query']['from']['username']."&tgBotApiToken=".$tgBotApiToken
    ),
    "ssl"=>array(
      "verify_peer"=>false,
      "verify_peer_name"=>false,
    )
  );
  $context=stream_context_create($opts);
  $addrEnd=strpos($data['callback_query']['data'],"act-");
  $srvId=substr($data['callback_query']['data'],4,($addrEnd-5));
  $file=file_get_contents('https://'.$tgBotServersArray[$srvId].'/webhook.php', true, $context);
  sendTelegram('sendMessage', 
    array(
      'chat_id' => $chatId,
      'text' => '✅Git Stash trigger successfully sent!'
    ));
  die();
}
//--------------------------------------------------End of actions functions-------------------------------------------------------------------------------------------------------------------

//Gets a list of servers from config file and returns it as array
function getServerList() 
{
  global $tgBotServersArray, $arrayServers;
  foreach ($tgBotServersArray as $key => $value) {
    $arrayServers[$key]=['text'=>$value, 'callback_data'=>"srv-".$key.";"];
  }
  return json_encode(array(
    'inline_keyboard' => array($arrayServers),
    'one_time_keyboard' => TRUE,
    'resize_keyboard' => TRUE
  ));
}

//Gets a list of available actions from config file and returns it as array
function getActionsList($prefix) 
{
  global $tgBotActionsArray, $arrayActions;
  foreach ($tgBotActionsArray as $key => $value) {
    $arrayActions[$key]=['text'=>$value, 'callback_data'=>$prefix."act-".$key.";"];
  }
  return json_encode(array(
    'inline_keyboard' => array($arrayActions),
    'one_time_keyboard' => true,
    'resize_keyboard' => true
  ));
}

//Gets a list of sites from remote server. webhook.php should be there and API keys must be set.
function getSitesList($prefix) 
{
  global $tgBotApiToken, $data, $addrUrl,$tgBotServersArray;
  $opts = array(
    'http'=>array(
      'method'=>"POST",
      'header'=>"Content-Type: application/x-www-form-urlencoded\r\n".
                "User-Agent:XpyctTelegramBot/1.0",
      'content'=>"tgBotCall=listSites&tgBotApiToken=".$tgBotApiToken
    ),
    "ssl"=>array(
      "verify_peer"=>false,
      "verify_peer_name"=>false,
    )
  );
  $context=stream_context_create($opts);
  $addrEnd=strpos($data['callback_query']['data'],"act-");
  $srvId=substr($data['callback_query']['data'],4,($addrEnd-5));
  $file=file_get_contents('https://'.$tgBotServersArray[$srvId].'/webhook.php', true, $context);
  //cleaning out the array from unnecessary symbols
  $file = str_replace('"', '', $file);
  $file = str_replace('[', '', $file);
  $file = str_replace(']', '', $file);
  //exploding data to make an array
  $a1 = explode(',',$file);
  foreach ($a1 as $key => $value) {
    $arraySites[$key]=['text'=>$value, 'callback_data'=>$prefix."sit-".$value.";"];
  }
  return json_encode(array(
    'inline_keyboard' => array_chunk($arraySites, 2, false),
    'one_time_keyboard' => true,
    'resize_keyboard' => true
  ));
}

//1st menu
//1st step-Catch up the first query - serverList
if (!empty($data['message']['text'])) {
  $chatId=$data['message']['from']['id'];
  if($data['message']['text'] == "/listservers") {
    $srvList=getServerList();
    sendTelegram('sendMessage', 
      array(
        'chat_id' => $chatId,
        'text' => 'Select a server:',
        'parse_mode' => 'html',
        'reply_markup' => $srvList
      ));
    die();
 	}
  if($data['message']['text'] == "/help") {
    sendTelegram('sendMessage', 
      array(
        'chat_id' => $chatId,
        'text' => "Available bot commands:\n".
                  "/listservers - a list of servers available to work with\n".
                  "/help - show this help menu\n".
                  "Available actions:\n".
                  "MakePull - schedule a git pull from repository for selected site\n".
                  "GitStash - schedule a git stash command, to hide current changes in directory, then make Pull"
      ));
    die();
 	}
}

//2nd menu -Here catch up all pressed buttons
if (!empty($data['callback_query']['data'])) {
  $chatId=$data['callback_query']['from']['id'];
  //4th step - do an action
  if (strpos($data['callback_query']['data'],"sit-") !== false) {
    //Start preparation to make deceasion of an action futher
    $workingSiteBegin=strpos($data['callback_query']['data'],"sit-");
    $workingSite=substr($data['callback_query']['data'],$workingSiteBegin+4,-1);
    $actIdStart=strpos($data['callback_query']['data'],"act-");
    $actId=substr($data['callback_query']['data'],$actIdStart+4,1);
    //call the function according its ID
    call_user_func($tgBotActionsArray[$actId],array($actId));
    }
  //3rd step - show a sites list
  if (strpos($data['callback_query']['data'],"act-") !== false) {
    $sitesList=getSitesList($data['callback_query']['data']);
    //looking or array id of Actions array
    $actIdStart=strpos($data['callback_query']['data'],"act-");
    $actId=substr($data['callback_query']['data'],$actIdStart+4,-1);
    //looking or array id of Servers array
    $srvId=substr($data['callback_query']['data'],4,1);
    sendTelegram('sendMessage', 
      array(
        'chat_id' => $chatId,
        'text' => 'Select a site on '.$tgBotServersArray[$srvId].' where we gonna '.$tgBotActionsArray[$actId].' do:',
        'parse_mode' => 'html',
        'reply_markup' => $sitesList
      ));
      die();
    }
  //2nd step - show an actions list
  if (strpos($data['callback_query']['data'],"srv-") !== false) {
  $actList=getActionsList($data['callback_query']['data']);
  $srvId=substr($data['callback_query']['data'],4,-1);
  sendTelegram('sendMessage', 
    array(
      'chat_id' => $chatId,
      'text' => 'Select an action to do on '.$tgBotServersArray[$srvId].':',
      'parse_mode' => 'html',
      'reply_markup' => $actList
    ));
    die();
  }
}

?>