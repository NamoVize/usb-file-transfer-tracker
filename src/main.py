#!/usr/bin/env python3
"""
USB File Transfer Tracker
Main application entry point
"""

import os
import sys
import json
import time
import argparse
import threading
from pathlib import Path

# Internal modules
from utils.logger import setup_logger
from utils.config import load_config, save_config, Config
from core.usb_monitor import USBMonitor
from core.file_watcher import FileWatcher
from ui.tray_app import setup_tray

# Global variables
logger = None
config = None
usb_monitor = None
file_watcher = None
stop_event = threading.Event()

def create_default_directories():
    """Create necessary directories if they don't exist"""
    # Create logs directory
    log_dir = Path(config.general.log_directory)
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Create any other required directories
    os.makedirs('data', exist_ok=True)

def initialize_system():
    """Initialize the system components"""
    global logger, config, usb_monitor, file_watcher
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    logger = setup_logger(config.general.log_directory)
    logger.info("Starting USB File Transfer Tracker")
    
    # Create necessary directories
    create_default_directories()
    
    # Initialize USB monitor
    usb_monitor = USBMonitor(config, logger)
    
    # Initialize file watcher
    file_watcher = FileWatcher(config, logger, usb_monitor)
    
    # Log startup information
    logger.info(f"Configuration loaded from {os.path.abspath('config.json')}")
    logger.info(f"Log files will be stored in {os.path.abspath(config.general.log_directory)}")

def start_monitoring():
    """Start the monitoring threads"""
    # Start USB monitor
    usb_monitor_thread = threading.Thread(target=usb_monitor.start_monitoring, 
                                          args=(stop_event,), 
                                          name="USBMonitorThread",
                                          daemon=True)
    usb_monitor_thread.start()
    
    # Start file watcher
    file_watcher_thread = threading.Thread(target=file_watcher.start_monitoring, 
                                           args=(stop_event,),
                                           name="FileWatcherThread",
                                           daemon=True)
    file_watcher_thread.start()
    
    logger.info("All monitoring services started")
    return usb_monitor_thread, file_watcher_thread

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='USB File Transfer Tracker')
    parser.add_argument('--no-tray', action='store_true', help='Run without system tray icon')
    parser.add_argument('--config', type=str, help='Path to custom config file')
    return parser.parse_args()

def main():
    """Main application entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Handle custom config location
    if args.config:
        Config.CONFIG_PATH = args.config
    
    # Initialize the system
    initialize_system()
    
    # Start monitoring threads
    monitor_thread, watcher_thread = start_monitoring()
    
    try:
        # If system tray is enabled and not disabled by arguments
        if config.general.minimize_to_tray and not args.no_tray:
            # Create system tray application
            tray_app = setup_tray(config, logger, stop_event)
            tray_app.run()
        else:
            # Run in console mode
            logger.info("Running in console mode. Press Ctrl+C to exit.")
            while not stop_event.is_set():
                time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        # Clean shutdown
        logger.info("Shutting down USB File Transfer Tracker")
        stop_event.set()
        
        # Wait for threads to finish
        monitor_thread.join(timeout=2)
        watcher_thread.join(timeout=2)
        
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()