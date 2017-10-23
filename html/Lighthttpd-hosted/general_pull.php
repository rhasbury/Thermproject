<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    
    $server = mysql_connect($host, $username, $password);
    $connection = mysql_select_db($database, $server);

	$type = $_GET['type'];

	switch ($type) {

		case "temp":			
			
				$myquery = "
					SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', temperature AS 'y', zone  FROM tempdat ORDER by tdate DESC LIMIT 1000
					";
				break;

			
		case "press":			
			
				$myquery = "
					SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_press AS 'y', zone FROM  ag_press_daily WHERE zone LIKE 'Living Room' ORDER by tdate DESC LIMIT 4000
					";
				break;

		case "humidity":						
				$myquery = "
					SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_humidity AS 'y', zone FROM  ag_hum_daily ORDER by tdate DESC LIMIT 2000
					";
				break;
		
		
		case "gas":						
				$myquery = "
					SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', gasreading AS 'y', type AS 'zone' FROM gasdat ORDER by tdate DESC LIMIT 3000
					";
				break;
			
		case "light":						
				$myquery = "
					SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', lightlevel AS 'y', zone FROM lightdat ORDER by tdate DESC LIMIT 300
					";
				break;
		default:
			echo "no argument";
			exit ();
			
	}

	
			

	error_log($myquery , 0);
    $query = mysql_query($myquery);
    
    if ( ! $query ) {
        echo mysql_error();
        die;
    }
    
    $data = array();
    
    for ($x = 0; $x < mysql_num_rows($query); $x++) {
        $data[] = mysql_fetch_assoc($query);
    }
    
    echo json_encode($data);     
     
    mysql_close($server);
?>
