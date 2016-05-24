<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    
    $server = mysql_connect($host, $username, $password);
    $connection = mysql_select_db($database, $server);


	$date = $_GET['date'];
	$equipment = $_GET['equipment'];

	$myquery = "SELECT SUM(rtime) as 'tdelta' FROM controldat WHERE state is false AND equipment LIKE  '" . $equipment . "'  AND DAY(tdate) = DAY('" . $date . "') ORDER BY tdate DESC LIMIT 1000";
 
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
