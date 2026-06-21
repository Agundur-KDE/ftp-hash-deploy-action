<?php

error_reporting(0);
header('Content-Type: application/json');
header('X-Powered-By: BonsaiPress');

$basePath = realpath(__DIR__);

if (isset($_GET['include']) && !empty($_GET['include'])) {
    $basePath = realpath(__DIR__ . '/../include');
}

if ($basePath === false || !is_dir($basePath)) {
    http_response_code(404);
    echo json_encode(['error' => 'path not found']);
    exit;
}

$me     = basename(__FILE__);
$hashes = [];

$it = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($basePath, RecursiveDirectoryIterator::SKIP_DOTS),
    RecursiveIteratorIterator::SELF_FIRST
);

foreach ($it as $file) {
    if (!$file->isFile() || $file->isLink()) {
        continue;
    }
    if ($file->getFilename() === $me || str_starts_with($file->getFilename(), '.')) {
        continue;
    }

    $rel     = ltrim(str_replace($basePath, '', $file->getPathname()), DIRECTORY_SEPARATOR);
    $content = (string) file_get_contents($file->getPathname());
    $content = str_replace("\r\n", "\n", $content);
    $hashes[$rel] = sha1('blob ' . strlen($content) . "\0" . $content);
}

echo json_encode($hashes, JSON_INVALID_UTF8_SUBSTITUTE);
