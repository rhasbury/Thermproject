<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);


	$date = $_GET['date'];
	$equipment = $_GET['equipment'];

	$myquery = "SELECT runtime_s as 'tdelta' FROM ag_control_daily AND equipment LIKE  '" . $equipment . "'  AND DATE(tdate) = DATE('" . $date . "') ORDER BY tdate DESC LIMIT 1000";
 
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
