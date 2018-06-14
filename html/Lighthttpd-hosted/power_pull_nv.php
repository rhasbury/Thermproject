<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);

    $myquery = "
SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', powerreading AS 'y', type AS type FROM powerdat ORDER by tdate DESC LIMIT 3000
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
