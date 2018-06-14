<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "192.168.1.104";
    $database="temps";
    
	$mysqli = new mysqli($host, $username, $password, $database);

    $myquery = "
SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', SUM(`powerreading`) as 'y' FROM powerdat WHERE type like '240v Total' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20
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

	    $myquery = "
SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', SUM(`powerreading`) as 'y' FROM powerdat WHERE type like '120v Total' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20
";

	error_log($myquery , 0);
    $result = $mysqli->query($myquery);
	
    if ( ! $result ) {
        echo $mysqli->error;
        die;
    }
    
    $data2 = array();
   

     for ($x = 0; $x < $result->num_rows; $x++) {
        $data2[] = $result->fetch_assoc();
    }

	$data3 = array(

			(object)  array(key => "120vTotal", values => $data2),
			(object)  array(key => "240vTotal", values => $data)

			);

    
    echo json_encode($data3);     

     
    $mysqli->close();
?>
