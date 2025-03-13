"""
System tray application for USB File Transfer Tracker
"""

import os
import sys
import time
import webbrowser
import threading
import subprocess
from pathlib import Path
from datetime import datetime

import pystray
from PIL import Image, ImageDraw

from ui.log_viewer import open_log_viewer
from ui.settings import open_settings
from utils.config import save_config

# Icon data (1px transparent placeholder for now)
ICON_DATA = b"""
iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABGdBTUEAALGPC/xhBQAAACBjSFJN
AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAABmJLR0QA/wD/AP+gvaeTAAAA
B3RJTUUH5QoTDDcvkgOJRQAAAVtJREFUWMPtlzFuwzAMRZ9bdOgFMnbxBXyDHqVHydCTZMgJeoae
wHOGAD5I96xtWtsh7UAQiLJISqLyvySsqmzZ3+/e9+yoql43m8MR2AJPwMPMmTPwCZyA43F/fv3L
eZFG3HYAR+AFWM3sRuAEnKKPJQ+kqdcduV2nLGSzORxF5EN/I75F5PW4P7+lPLDYPxVUNeV4qHNV
Paq7j8VgPqfGFbgPxvwYtYl4UHc/iUiqmxgc/wR2Fs52wHtbHugZl7XA8V3CeHKS2vKB46nJo4I6
dTxo8h+7gXpxx9fAfcvWBk0uxYyvgV1KQNPE6c8mgXiTL9txGjJ5RcJYsncshkw+J/EtcCs+iy2I
5FUXEFbJ3xwXmZx6AFOTuzlOmoB6ctEkczxoP0wBlpxs0OQL+Beo7gLnJMj9MvKCmMDbXEYw/kXR
JBC/jGCi/4KYYAoW/xfEFL9jKyY46gX6xnccjR/dXoJu37nhFwAAAABJRU5ErkJggg==
"""

def create_image():
    """Create system tray icon image"""
    # You can replace this with a proper icon
    # For now, creating a simple icon with USB symbol
    width = 64
    height = 64
    image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Draw USB symbol (simplified)
    dc.rectangle((24, 16, 40, 24), fill=(50, 120, 220))
    dc.rectangle((28, 24, 36, 44), fill=(50, 120, 220))
    dc.rectangle((20, 44, 44, 48), fill=(50, 120, 220))
    
    return image

def open_logs_directory(config):
    """Open logs directory in file explorer"""
    log_dir = Path(config.general.log_directory).absolute()
    
    try:
        if sys.platform == 'win32':
            os.startfile(log_dir)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', log_dir])
        else:  # Linux
            subprocess.call(['xdg-open', log_dir])
    except Exception as e:
        print(f"Error opening logs directory: {str(e)}")

def setup_tray(config, logger, stop_event):
    """Set up and return system tray icon"""
    
    def on_clicked(icon, item):
        if item.text == "Exit":
            stop_event.set()
            icon.stop()
        elif item.text == "View Logs":
            open_log_viewer(config, logger)
        elif item.text == "Open Logs Directory":
            open_logs_directory(config)
        elif item.text == "Settings":
            if open_settings(config, logger):
                # Config was changed, save it
                save_config(config)
                logger.info("Configuration updated")
    
    # Create the icon
    icon = pystray.Icon("usb_tracker")
    icon.title = "USB File Transfer Tracker"
    
    # Set the icon image (from ICON_DATA or create a new one)
    try:
        icon.icon = create_image()
    except Exception as e:
        logger.error(f"Error creating icon: {str(e)}")
        # Fallback to a simple image
        img = Image.new('RGB', (64, 64), color=(50, 120, 220))
        icon.icon = img
    
    # Create menu
    icon.menu = pystray.Menu(
        pystray.MenuItem("USB File Transfer Tracker", None, enabled=False),
        pystray.MenuItem("View Logs", on_clicked),
        pystray.MenuItem("Open Logs Directory", on_clicked),
        pystray.MenuItem("Settings", on_clicked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_clicked)
    )
    
    # Add notification on startup
    def notify_startup():
        time.sleep(1)
        icon.notify("USB File Transfer Tracker is running in the background",
                   "The application is monitoring USB devices for file transfers")
    
    threading.Thread(target=notify_startup, daemon=True).start()
    
    # Return the icon for running in the main thread
    return icon