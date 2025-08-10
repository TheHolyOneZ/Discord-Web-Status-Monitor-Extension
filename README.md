# Discord & Web Status Monitor

This project provides a complete, automated system for monitoring your services and displaying their status on both a dedicated Discord channel and a beautiful, public-facing webpage. It's designed to be powerful yet easy to manage, with nearly all configuration handled directly within Discord.

It consists of two main parts:
1.  **A Python Discord Bot**: A `discord.py` cog that acts as the "heartbeat" of the system. It actively checks configured services, updates a status message in Discord, and securely sends the data to your web frontend.
2.  **A PHP Web Frontend**: A pair of PHP scripts that receive, store, and render the status data on a stylish, responsive page built with Tailwind CSS.

![How it looks](<img width="1247" height="1280" alt="image" src="https://github.com/user-attachments/assets/e96edd36-5aa7-41db-a70e-2aac583933f8" />)

---

## How It Works: The Data Flow

Understanding the flow of information is key to using this project effectively.

1.  **The Heartbeat (Python Bot)**
    -   A background task (`tasks.loop`) runs at a configurable interval (e.g., every 5 minutes).
    -   During each cycle, it uses the `aiohttp` library to asynchronously check the status of all monitored items:
        -   **Discord Bots**: Fetches the live presence (`Online`, `Idle`, `Offline`) from your server.
        -   **Websites**: Sends an HTTP request to each URL to see if it returns a success code (200-299).
        -   **Discord Services**: Pulls real-time data directly from Discord's official JSON endpoint.
        -   **Custom Services**: Reads the manually set status for any other items.

2.  **The Bridge (Secure API Call)**
    -   The bot gathers all the status information into a single JSON object.
    -   It then sends this JSON data via an HTTP `POST` request to your `receive_status.php` endpoint.
    -   To ensure security, it includes a **Secret Token** in the URL. Your PHP script will reject any request that doesn't have the correct token.

3.  **The Receiver & Storage (PHP Backend)**
    -   `receive_status.php` is a simple, secure endpoint. Its only job is to receive data.
    -   It first checks if the `SECRET_TOKEN` from the request matches the one defined in the file.
    -   If the token is valid, it takes the raw JSON data from the bot and writes it into the `status.json` file, overwriting the old data. **This file is created automatically on the first successful request.**

4.  **The Display (PHP Frontend)**
    -   When a user visits `index.php`, the script reads and parses the `status.json` file.
    -   It calculates an overall system status (e.g., "All Systems Operational," "Partial Service Disruption").
    -   It then dynamically builds the webpage, using helper functions to apply the correct colors, icons, and text for each service based on its current status. The page is designed with Tailwind CSS for a modern, responsive look and auto-refreshes every 60 seconds.

---

## Setup and Configuration

The setup is designed to be fast and simple. **You only need to edit one line of code.** After that, everything is managed from Discord.

### Prerequisites
-   **Python 3.11 - 3.12.7**
-   A **web server with PHP support** (e.g., Apache, Nginx).
-   A Discord Bot application with a Token.
    -   **Privileged Gateway Intents** (Presence Intent and Server Members Intent) must be enabled for your bot on the Discord Developer Portal.

### Step 1: Prepare Your Web Server (The Only Edit You'll Make)
1.  **Upload Files**: Upload `index.php` and `receive_status.php` to a public directory on your web server.
2.  **Create Your Secret Token**: Open `receive_status.php` in a text editor. On line 3, **change the value of `SECRET_TOKEN`** to a long, random, and secure password.
    ```php
    // receive_status.php
    define('SECRET_TOKEN', 'Your-Unique-And-Very-Secure-Password-Here-123!');
    ```
    This is the master key that allows the bot to talk to your website. **Copy this token for the next step.**

### Step 2: Configure the Bot in Discord
1.  **Install Libraries & Run Bot**:
    ```bash
    pip install discord.py aiohttp
    ```
    Add the `Discord-Statuses-website.py` cog to your bot and run it.

2.  **Open the Admin Panel**: In your Discord server, type the `!status-setup` command. A control panel only you can see will appear.

3.  **Link the Bot to Your Website**:
    -   Click the **API Settings** button.
    -   For `API POST URL`, enter the full, public URL to your `receive_status.php` file (e.g., `https://yourdomain.com/status/receive_status.php`).
    -   For `Secret Token`, paste the **exact same secret token** you created in the PHP file.

4.  **Finalize in Discord**:
    -   Use the **Post/Move Status** button to select the channel for your status embed.
    -   Use the **Manage...** buttons to add the bots, websites, and services you want to monitor.

**That's it!** The bot will now automatically update the Discord embed and your public webpage.

---

## The Admin Panel: Your Control Center

The `!status-setup` command is your one-stop shop for managing the monitor.

-   **Manage Bots/Websites/Services**: Add or remove items to be monitored.
-   **Discord Services**: Select which of Discord's official services you want to display.
-   **Remove Item**: A quick way to remove any monitored item.
-   **Post/Move Status**: Sets or changes the channel where the status embed is posted.
-   **API Settings**: Configure the URL and secret token to link the bot to your website.
-   **Set Interval**: Change how often the bot checks for status updates (from 1 to 60 minutes).
-   **Change Title**: Customize the title of the Discord status embed.
-   **Refresh & POST**: Manually force an immediate status check and push the update to your website.
