<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
    $database="temps";
    
    $server = mysql_connect($host, $username, $password);
    $connection = mysql_select_db($database, $server);


    $myquery = "
SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', SUM(`powerreading`) as 'y' FROM powerdat WHERE type like '240v Total' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20
";

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

	    $myquery = "
SELECT UNIX_TIMESTAMP(DATE(tdate)) as 'x', SUM(`powerreading`) as 'y' FROM powerdat WHERE type like '120v Total' GROUP BY  DATE(tdate) ORDER BY tdate DESC LIMIT 20
";

	error_log($myquery , 0);
    $query = mysql_query($myquery);
    
    if ( ! $query ) {
        echo mysql_error();
        die;
    }
    
    $data2 = array();
    
    for ($x = 0; $x < mysql_num_rows($query); $x++) {
        $data2[] = mysql_fetch_assoc($query);
    }

	$data3 = array(

			(object)  array(key => "120vTotal", values => $data2),
			(object)  array(key => "240vTotal", values => $data)

			);

    
    echo json_encode($data3);     

     
    mysql_close($server);
?>
