/**
 * Setup script for the USB File Transfer Tracker
 * Helps with setting up autostart and other system configurations
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');
const readline = require('readline');

// Setup readline interface
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

const isWindows = process.platform === 'win32';
const isMac = process.platform === 'darwin';
const isLinux = process.platform === 'linux';

/**
 * Main setup function
 */
async function setup() {
    console.log('USB File Transfer Tracker - Setup');
    console.log('=================================');
    console.log('This script will help you set up the USB File Transfer Tracker application.');
    console.log('');

    try {
        // Create logs directory if it doesn't exist
        const logsDir = path.join(process.cwd(), 'logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir);
            console.log('✓ Created logs directory');
        }

        // Ask if the user wants to set up autostart
        const setupAutostart = await askQuestion('Do you want to set up the application to run at system startup? (y/n): ');
        
        if (setupAutostart.toLowerCase() === 'y') {
            await setupAutostartForPlatform();
        }

        console.log('');
        console.log('Setup complete!');
        console.log('');
        console.log('To run the application, use:');
        if (isWindows) {
            console.log('python src/main.py');
        } else {
            console.log('python3 src/main.py');
        }
        console.log('');
        console.log('For more information, please refer to the README.md file.');
    } catch (error) {
        console.error('Error during setup:', error.message);
    } finally {
        rl.close();
    }
}

/**
 * Set up autostart based on the platform
 */
async function setupAutostartForPlatform() {
    if (isWindows) {
        await setupWindowsAutostart();
    } else if (isMac) {
        await setupMacAutostart();
    } else if (isLinux) {
        await setupLinuxAutostart();
    } else {
        console.log('❌ Automatic startup setup is not supported for your platform.');
        console.log('   Please refer to your system documentation to set up applications to run at startup.');
    }
}

/**
 * Set up autostart for Windows
 */
async function setupWindowsAutostart() {
    try {
        const appPath = path.join(process.cwd(), 'src', 'main.py');
        const startupDir = path.join(os.homedir(), 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup');
        const shortcutPath = path.join(startupDir, 'USBFileTransferTracker.bat');

        // Create a batch file that starts the application
        const batchContent = `@echo off
cd /d "${process.cwd()}"
start pythonw "${appPath}"
`;

        fs.writeFileSync(shortcutPath, batchContent);
        console.log('✓ Added application to Windows startup');
    } catch (error) {
        console.error('❌ Failed to set up Windows autostart:', error.message);
    }
}

/**
 * Set up autostart for macOS
 */
async function setupMacAutostart() {
    try {
        const appPath = path.join(process.cwd(), 'src', 'main.py');
        const launchAgentsDir = path.join(os.homedir(), 'Library', 'LaunchAgents');
        
        // Create LaunchAgents directory if it doesn't exist
        if (!fs.existsSync(launchAgentsDir)) {
            fs.mkdirSync(launchAgentsDir, { recursive: true });
        }
        
        const plistPath = path.join(launchAgentsDir, 'com.namovize.usb-file-transfer-tracker.plist');
        
        // Create plist file
        const plistContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.namovize.usb-file-transfer-tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${appPath}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${process.cwd()}</string>
    <key>StandardOutPath</key>
    <string>${path.join(process.cwd(), 'logs', 'startup.log')}</string>
    <key>StandardErrorPath</key>
    <string>${path.join(process.cwd(), 'logs', 'startup_error.log')}</string>
</dict>
</plist>`;

        fs.writeFileSync(plistPath, plistContent);
        
        // Load the launch agent
        execSync(`launchctl load ${plistPath}`);
        
        console.log('✓ Added application to macOS startup');
    } catch (error) {
        console.error('❌ Failed to set up macOS autostart:', error.message);
    }
}

/**
 * Set up autostart for Linux
 */
async function setupLinuxAutostart() {
    try {
        const appPath = path.join(process.cwd(), 'src', 'main.py');
        const autostartDir = path.join(os.homedir(), '.config', 'autostart');
        
        // Create autostart directory if it doesn't exist
        if (!fs.existsSync(autostartDir)) {
            fs.mkdirSync(autostartDir, { recursive: true });
        }
        
        const desktopPath = path.join(autostartDir, 'usb-file-transfer-tracker.desktop');
        
        // Create desktop entry file
        const desktopContent = `[Desktop Entry]
Type=Application
Name=USB File Transfer Tracker
Comment=Monitors USB file transfers for security
Exec=/usr/bin/python3 ${appPath}
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
`;

        fs.writeFileSync(desktopPath, desktopContent);
        fs.chmodSync(desktopPath, '0755');
        
        console.log('✓ Added application to Linux startup');
    } catch (error) {
        console.error('❌ Failed to set up Linux autostart:', error.message);
    }
}

/**
 * Helper function to ask a question and get a response
 */
function askQuestion(question) {
    return new Promise((resolve) => {
        rl.question(question, (answer) => {
            resolve(answer);
        });
    });
}

// Run the setup
setup();