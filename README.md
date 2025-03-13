# USB File Transfer Tracker

A system that logs which files were copied to or from a USB drive, with timestamps and file names, to prevent unauthorized data leaks.

## Features

- Real-time monitoring of USB drive connections and disconnections
- Tracking of all file operations (copy, move, delete) to/from USB drives
- Detailed logging with timestamps, file names, file sizes, and operation types
- Secure log storage with tamper-evident features
- Optional alerts for suspicious file transfer activities
- Cross-platform support (Windows, macOS, Linux)
- Simple configuration through a user-friendly interface

## Requirements

- Python 3.8 or higher
- Administrative/root privileges (required for USB device monitoring)

## Installation

### Windows

1. Clone this repository:
   ```
   git clone https://github.com/NamoVize/usb-file-transfer-tracker.git
   cd usb-file-transfer-tracker
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### macOS/Linux

1. Clone this repository:
   ```
   git clone https://github.com/NamoVize/usb-file-transfer-tracker.git
   cd usb-file-transfer-tracker
   ```

2. Create a virtual environment and activate it:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Starting the Tracker

1. With your virtual environment activated, run:
   ```
   python src/main.py
   ```

2. For first-time setup, the application will guide you through a configuration process or you can modify the `config.json` file directly.

3. The application will minimize to the system tray and run in the background, monitoring USB devices and file transfers.

### Viewing Logs

1. Logs are stored in the `logs` directory by default.
2. You can view logs through the application GUI by right-clicking the system tray icon and selecting "View Logs".
3. Log files are in CSV format and can also be opened with any spreadsheet software.

### Configuration Options

Edit the `config.json` file to customize these settings:
- Log location
- Alert thresholds
- File type monitoring rules
- Exclusion paths

## Security Considerations

- Log files are hashed to detect tampering
- The application requires administrative privileges to function properly
- No data is sent outside of your local system

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is designed for legitimate security monitoring purposes. Always ensure you comply with local laws and organizational policies regarding monitoring and data privacy.