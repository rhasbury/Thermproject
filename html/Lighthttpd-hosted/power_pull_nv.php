<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);


    $myquery = "
SELECT  UNIX_TIMESTAMP(`tdate`) AS 'x', powerreading AS 'y', type AS type FROM powerdat ORDER by tdate DESC LIMIT 3000
";


	error_log($myquery , 0);
    $query = $mysqli->query($myquery);
    
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
