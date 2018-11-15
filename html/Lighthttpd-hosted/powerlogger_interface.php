
<?php

	if(!($sock = socket_create(AF_INET, SOCK_STREAM, 0))){
		$errorcode = socket_last_error();
		$errormsg = socket_strerror($errorcode);
     
		die("Couldn't create socket: [$errorcode] $errormsg \n");
	} 
	
	
	if(!socket_connect($sock , 'localhost' , 50008)){
	
    $errorcode = socket_last_error();
    $errormsg = socket_strerror($errorcode);
     
    die("Could not connect: [$errorcode] $errormsg \n");
	}
 
		
	$message = "get_powers";
	//$message = "get_something";
	//$message = $_GET['command'];
 
	//Send the message to the server
	if( ! socket_send ( $sock , $message , strlen($message) , 0))
	{
		$errorcode = socket_last_error();
		$errormsg = socket_strerror($errorcode);
		 
		die("Could not send data: [$errorcode] $errormsg \n");
	}
	 
	
	
	//Now receive reply from server
	if(socket_recv ( $sock , $buf , 100045 , MSG_WAITALL ) === FALSE)
	{
		$errorcode = socket_last_error();
		$errormsg = socket_strerror($errorcode);
		 
		die("Could not receive data: [$errorcode] $errormsg \n");
	}
	 
	//print the received message
	echo $buf;
	
	socket_close($sock);
?>
