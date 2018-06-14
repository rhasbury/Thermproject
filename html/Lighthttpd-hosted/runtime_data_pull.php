<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
	
	$mysqli = new mysqli($host, $username, $password, $database);

	if(isset($_GET["equipment"])){
		$equipment = $_GET['equipment'];
		$myquery = "SELECT tdate, rtime FROM controldat WHERE state is false AND equipment LIKE  '" . $equipment . "'  ORDER by tdate DESC LIMIT 3000";
	}
	else {
		$myquery = "SELECT tdate, rtime, equipment FROM controldat WHERE state is false ORDER by tdate DESC LIMIT 300";
	}
	
	
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
