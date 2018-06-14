<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
	
	$mysqli = new mysqli($host, $username, $password, $database);

//    $myquery = "
//SELECT  `date`, `close` FROM  `data2`
//";

//$date = '2015-05-12';

//    $myquery = "
//SELECT  UNIX_TIMESTAMP(`tdate`) AS 'fix_time', 'zone', 'temperature'  FROM  `tempdat` WHERE tdate LIKE " . "'" . $date . "%'" . " ORDER by tdate DESC LIMIT 6000
//";

// Order by was killing my temps database for some reason. Removed. 

    $myquery = "
SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', pressure AS 'y', zone FROM  pressdat WHERE zone LIKE 'Living Room' ORDER by tdate DESC LIMIT 25000
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
