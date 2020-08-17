<?php
    $username = "monitor"; 
    $password = "password";   
    $host = "localhost";
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
