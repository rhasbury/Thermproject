<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);


    $myquery = "
SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', `kwhtotal` as 'y' FROM ag_power_daily ORDER BY tdate DESC LIMIT 100
";


	error_log($myquery , 0);
    $query = mysqli_query($myquery);
    
    if ( ! $query ) {
        echo mysqli_error();
        die;
    }
    
    $data = array();
    
    for ($x = 0; $x < mysqli_num_rows($query); $x++) {
        $data[] = mysqli_fetch_assoc($query);
    }
    
    echo json_encode($data);     
     
    mysqli_close($server);
?>
