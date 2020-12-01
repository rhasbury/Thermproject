<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    

	$mysqli = new mysqli($host, $username, $password, $database);
	
	
	$type = $_GET['type'];

	if(isset($_GET['zone']) && !empty($_GET['zone'])){ 	   
		$zone =  " WHERE zone LIKE '".$_GET['zone']."' ";
		
		} 
	else {
    	$zone = " ";
		}		


	if(isset($_GET['limit']) && !empty($_GET['limit'])){ 	   
		$limit =  $_GET['limit'];
		
		} 
	else {
    	$limit = "2000";
		}		
		

	if(isset($_GET['daily'])){
		switch ($type) { 	   
			case "temp":			

					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_temp AS 'y', zone  FROM ag_temp_daily".$zone."ORDER by tdate DESC LIMIT ".$limit;						
					break;


			case "press":			

					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_press AS 'y', zone FROM  ag_press_daily WHERE zone LIKE 'Living Room' ORDER by tdate DESC LIMIT ".$limit;						
					break;

			case "humidity":						
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_humidity AS 'y', zone FROM  ag_hum_daily ORDER by tdate DESC LIMIT ".$limit;
					break;


			case "gas":						
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', gasreading AS 'y', type AS 'zone' FROM gasdat ORDER by tdate DESC LIMIT ".$limit;						
					break;

			case "light":						
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', lightlevel AS 'y', zone FROM lightdat ORDER by tdate DESC LIMIT ".$limit;						
					break;
			default:
				echo "no argument";
				exit ();

		
		} 
	}
	else {			
		switch ($type) {

			case "temp":			

					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', temperature AS 'y', zone  FROM tempdat".$zone."ORDER by tdate DESC LIMIT ".$limit;
					break;

			case "temp2":			

					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', temperature AS 'y', zone  FROM tempdat2".$zone."ORDER by tdate DESC LIMIT ".$limit;
					break;
			
			case "temp3":			
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', temperature AS 'y', zone  FROM tempdat3".$zone."ORDER by tdate DESC LIMIT ".$limit;
					break;                
			case "press":			

					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_press AS 'y', zone FROM  ag_press_daily WHERE zone LIKE 'Living Room' ORDER by tdate DESC LIMIT ".$limit;
					break;

			case "humidity":						
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', average_humidity AS 'y', zone FROM  ag_hum_daily ORDER by tdate DESC LIMIT ".$limit;
					break;


			case "gas":						
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', gasreading AS 'y', type AS 'zone' FROM gasdat ORDER by tdate DESC LIMIT ".$limit;
					break;

			case "light":						
					$myquery = "
						SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', lightlevel AS 'y', zone FROM lightdat ORDER by tdate DESC LIMIT ".$limit;
					break;
			default:
				echo "no argument";
				exit ();

		}
	}
	
			

	error_log($myquery , 0);
    
    $result = $mysqli->query($myquery);
	
    if ( ! $result ) {
        echo $mysqli->error
        die;
    }
    
    $data = array();
    
    for ($x = 0; $x < $result->num_rows; $x++) {
        $data[] = $result->fetch_assoc();
    }
    
    echo json_encode($data);     
     
    $mysqli->close();
?>
