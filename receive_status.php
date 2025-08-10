<?php

define('SECRET_TOKEN', '9iu3nTA3OMpb16TAHYLK3pFgF4ZY1VSy');

$outputFile = 'status.json';

header('Content-Type: text/plain');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405); 
    die('Error: This endpoint only accepts POST requests.');
}

$token = $_GET['token'] ?? null;

if (!$token) {
    http_response_code(401); 
    die('Error: Secret token is missing from the URL.');
}

if ($token !== SECRET_TOKEN) {
    http_response_code(403);
    die('Error: Invalid secret token.');
}

$jsonPayload = file_get_contents('php://input');
if ($jsonPayload === false || empty($jsonPayload)) {
    http_response_code(400);
    die('Error: No data received in the request body.');
}

json_decode($jsonPayload);
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400); 
    die('Error: Invalid JSON format received.');
}

if (file_put_contents($outputFile, $jsonPayload, LOCK_EX) === false) {
    http_response_code(500); 
    die('Error: Could not write data to the status file. Check server permissions.');
}

http_response_code(200); 
echo 'Success: Status data received and updated successfully.';

?>
