<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
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
    $query = $mysqli->query($myquery);
    
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
