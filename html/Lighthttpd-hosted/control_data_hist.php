<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    
    $server = mysql_connect($host, $username, $password);
    $connection = mysql_select_db($database, $server);


	$equipment = $_GET['equipment'];


	$myquery = "SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', SUM(`rtime`) as 'y' FROM controldat WHERE state is false AND equipment LIKE  '" . $equipment . "' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20";

	// "SELECT DATE(tdate) as 'x', SUM(`rtime`) as 'y' FROM controldat WHERE state is false AND equipment LIKE  'fan' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20"
		
 
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
