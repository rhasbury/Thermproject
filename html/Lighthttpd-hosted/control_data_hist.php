<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);

	$equipment = $_GET['equipment'];


	$myquery = "SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', SUM(`rtime`) as 'y' FROM controldat WHERE state is false AND equipment LIKE  '" . $equipment . "' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20";

	// "SELECT DATE(tdate) as 'x', SUM(`rtime`) as 'y' FROM controldat WHERE state is false AND equipment LIKE  'fan' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20"
		
 
	error_log($myquery , 0);
    $result = $mysqli->query($myquery);
    
    if ( ! $result ) {
        echo $mysqli->error;
        die;
    }
    
    
    $data = array();
    
    
    for ($x = 0; $x < $result->num_rows; $x++) {
        $data[] = $result->fetch_assoc();
    }
    
    echo json_encode($data);     
     
    $mysqli->close();
?>
