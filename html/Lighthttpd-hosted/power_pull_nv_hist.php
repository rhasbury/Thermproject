<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);


    $myquery = "
SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', `kwhtotal` as 'y' FROM ag_power_daily ORDER BY tdate DESC LIMIT 100
";


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
