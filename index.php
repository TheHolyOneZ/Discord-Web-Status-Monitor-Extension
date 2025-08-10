<?php

$statusFile = 'status.json';



/**
 * Reads and decodes the status data from the JSON file.
 * @param string $filePath The path to the status.json file.
 * @return array An associative array of the status data, or an empty array on failure.
 */
function getStatusData(string $filePath): array {
    if (!file_exists($filePath) || filesize($filePath) === 0) {
        return []; 
    }
    $jsonContent = file_get_contents($filePath);
    $data = json_decode($jsonContent, true);
    return json_last_error() === JSON_ERROR_NONE ? $data : [];
}

/**
 * Returns a set of Tailwind CSS classes based on the service status.
 * This function provides classes for text color, icon background, and border color.
 * @param string $status The status text (e.g., "Online", "Offline").
 * @return array An array of CSS classes.
 */
function getStatusStyles(string $status): array {
    $status = strtolower($status);
    if (str_contains($status, 'operational') || str_contains($status, 'online')) {
        return [
            'text' => 'text-cyan-300',
            'icon_bg' => 'bg-cyan-300/10',
            'border' => 'border-cyan-300/20',
            'dot' => 'bg-cyan-400'
        ];
    }
    if (str_contains($status, 'outage') && !str_contains($status, 'partial')) { 
        return [
            'text' => 'text-red-400',
            'icon_bg' => 'bg-red-400/10',
            'border' => 'border-red-400/20',
            'dot' => 'bg-red-500'
        ];
    }
    if (str_contains($status, 'partial') || str_contains($status, 'degraded')) { 
        return [
            'text' => 'text-amber-400',
            'icon_bg' => 'bg-amber-400/10',
            'border' => 'border-amber-400/20',
            'dot' => 'bg-amber-400'
        ];
    }
    if (str_contains($status, 'maintenance')) {
        return [
            'text' => 'text-blue-400',
            'icon_bg' => 'bg-blue-400/10',
            'border' => 'border-blue-400/20',
            'dot' => 'bg-blue-400'
        ];
    }

    return [
        'text' => 'text-gray-400',
        'icon_bg' => 'bg-gray-400/10',
        'border' => 'border-gray-400/20',
        'dot' => 'bg-gray-500'
    ];
}

/**
 * Maps a status string to a corresponding SVG icon.
 * @param string $status The status text.
 * @return string An SVG icon.
 */
function getStatusIcon(string $status): string {
    $status = strtolower($status);
    if (str_contains($status, 'operational') || str_contains($status, 'online')) {
        return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
    }
    if (str_contains($status, 'partial') || str_contains($status, 'degraded')) {
        return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
    }
    if (str_contains($status, 'offline') || str_contains($status, 'error') || str_contains($status, 'failed') || str_contains($status, 'outage')) {
        return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>';
    }
     if (str_contains($status, 'maintenance')) {
        return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>';
    }
    return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
}


/**
 * Calculates the overall system status based on all components.
 * @param array $data The full status data array.
 * @return array An array containing the overall status text and a style array.
 */
function getOverallStatus(array $data): array {
    $hasIssue = false;
    $hasOutage = false;

    $allComponents = array_merge(
        $data['bots'] ?? [],
        $data['websites'] ?? [],
        $data['discord_services'] ?? [],
        $data['custom_services'] ?? []
    );

    if (empty($allComponents)) {
        return ['text' => 'Awaiting Status Data', 'styles' => getStatusStyles('maintenance')];
    }

    foreach ($allComponents as $component) {
        $status = strtolower($component['status'] ?? '');
        if (str_contains($status, 'offline') || (str_contains($status, 'outage') && !str_contains($status, 'partial')) || str_contains($status, 'error')) {
            $hasOutage = true;
            break; 
        }
        if (str_contains($status, 'partial') || str_contains($status, 'degraded')) {
            $hasIssue = true;
        }
    }

    if ($hasOutage) {
        return ['text' => 'Major Service Outage', 'styles' => getStatusStyles('outage')];
    }
    if ($hasIssue) {
        return ['text' => 'Partial Service Disruption', 'styles' => getStatusStyles('partial')];
    }

    return ['text' => 'All Systems Operational', 'styles' => getStatusStyles('operational')];
}



$data = getStatusData($statusFile);
$overallStatus = getOverallStatus($data);
$lastUpdated = 'Never';
if (!empty($data['last_updated_utc'])) {
    try {
        $utcTime = new DateTime($data['last_updated_utc']);

        $localTimezone = new DateTimeZone('Europe/Berlin');
        $utcTime->setTimezone($localTimezone);
        $lastUpdated = $utcTime->format('F j, Y, g:i:s A T');
    } catch (Exception $e) {
        $lastUpdated = 'Invalid Date';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Zygnal Status Page</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
    <style>

        body {
            font-family: 'Inter', sans-serif;

            background-color: #0c0f1a;
            background-image: radial-gradient(circle at 1px 1px, rgba(200, 200, 255, 0.1) 1px, transparent 0);
            background-size: 2rem 2rem;
        }


        .glass-card {
            background: rgba(23, 27, 41, 0.5); 
            -webkit-backdrop-filter: blur(20px); 
            backdrop-filter: blur(20px); 
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 1.5rem; 
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }


        .status-glow-cyan {
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.2), inset 0 0 10px rgba(0, 255, 255, 0.1);
        }
        .status-glow-amber {
            box-shadow: 0 0 30px rgba(251, 191, 36, 0.2), inset 0 0 10px rgba(251, 191, 36, 0.1);
        }
        .status-glow-red {
            box-shadow: 0 0 30px rgba(248, 113, 113, 0.2), inset 0 0 10px rgba(248, 113, 113, 0.1);
        }
        .status-glow-blue {
            box-shadow: 0 0 30px rgba(96, 165, 250, 0.2), inset 0 0 10px rgba(96, 165, 250, 0.1);
        }
        .status-glow-gray {
            box-shadow: 0 0 30px rgba(156, 163, 175, 0.1), inset 0 0 10px rgba(156, 163, 175, 0.05);
        }


        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 9999px;
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        

        @keyframes pulse {
            50% {
                opacity: .5;
            }
        }
    </style>
</head>
<body class="text-gray-200">

    <div class="container mx-auto p-4 md:p-8 max-w-3xl">


        <header class="mb-8 text-center">
            <h1 class="text-5xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-500">Zygnal Status</h1>
            <p class="text-lg text-gray-400 mt-2">A live overview of our service status.</p>
        </header>


        <?php $overallStyles = $overallStatus['styles']; ?>
        <div class="glass-card p-6 mb-10 text-center transition-all duration-500 status-glow-<?php echo substr($overallStyles['dot'], 3); ?>">
            <div class="flex items-center justify-center gap-4">
                <div class="p-3 rounded-full <?php echo $overallStyles['icon_bg']; ?>">
                    <?php echo getStatusIcon($overallStatus['text']); ?>
                </div>
                <h2 class="text-2xl md:text-3xl font-bold <?php echo $overallStyles['text']; ?>">
                    <?php echo htmlspecialchars($overallStatus['text']); ?>
                </h2>
            </div>
        </div>
        

        <div class="glass-card p-4 md:p-6 space-y-6">
            <?php if (empty($data)): ?>
                <div class="text-center py-8">
                    <p class="text-gray-400">The first status report has not been received yet.</p>
                    <p class="text-gray-500 text-sm">This page will update automatically.</p>
                </div>
            <?php endif; ?>
            

            <?php
            $componentTypes = [
                'bots' => 'Bots',
                'websites' => 'Websites',
                'discord_services' => 'Discord Services',
                'custom_services' => 'Other Services'
            ];

            foreach ($componentTypes as $key => $title):
                if (!empty($data[$key])):
            ?>
            <section>
                <h3 class="text-xl font-bold text-gray-100 mb-4 px-2"><?php echo $title; ?></h3>
                <div class="space-y-3">
                    <?php foreach ($data[$key] as $item): ?>
                        <?php $styles = getStatusStyles($item['status']); ?>
                        <?php $isLink = ($key === 'websites'); ?>
                        
                        <<?php echo $isLink ? 'a' : 'div'; ?> <?php if ($isLink): ?>href="<?php echo htmlspecialchars($item['url']); ?>" target="_blank" rel="noopener noreferrer"<?php endif; ?> class="flex items-center justify-between p-4 rounded-xl border <?php echo $styles['border']; ?> bg-black/10 hover:bg-black/20 transition-all duration-300">
                            <div class="flex items-center gap-4">
                                <div class="p-2 rounded-full <?php echo $styles['icon_bg']; ?> <?php echo $styles['text']; ?>">
                                    <?php echo getStatusIcon($item['status']); ?>
                                </div>
                                <span class="font-semibold text-gray-200"><?php echo htmlspecialchars($item['label'] ?? $item['name']); ?></span>
                            </div>
                            <div class="flex items-center gap-2">
                                <div class="status-dot <?php echo $styles['dot']; ?>"></div>
                                <span class="font-medium <?php echo $styles['text']; ?>"><?php echo htmlspecialchars($item['status']); ?></span>
                            </div>
                        </<?php echo $isLink ? 'a' : 'div'; ?>>

                    <?php endforeach; ?>
                </div>
            </section>
            <?php 
                endif; 
            endforeach; 
            ?>
        </div>

        <footer class="text-center mt-10 text-gray-500 text-sm">
            <p>Last updated: <?php echo htmlspecialchars($lastUpdated); ?></p>
            <p class="mt-1 opacity-75">This page automatically refreshes every 60 seconds.</p>
        </footer>

    </div>

</body>
</html>
