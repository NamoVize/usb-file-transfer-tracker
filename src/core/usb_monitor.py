"""
USB Device monitoring module.
Handles detection of USB devices and provides information about them.
"""

import os
import sys
import time
import platform
import threading
from pathlib import Path
from datetime import datetime

# Cross-platform USB detection
if platform.system() == 'Windows':
    import wmi
    import win32file
    import win32con
elif platform.system() == 'Linux':
    import pyudev
elif platform.system() == 'Darwin':  # macOS
    import subprocess
    import plistlib

class USBDevice:
    """Representation of a USB storage device"""
    
    def __init__(self, device_id, name, mount_point, serial=None, vendor=None, model=None):
        self.device_id = device_id
        self.name = name
        self.mount_point = mount_point
        self.serial = serial
        self.vendor = vendor
        self.model = model
        self.connected_time = datetime.now()
    
    def __eq__(self, other):
        if not isinstance(other, USBDevice):
            return False
        return self.device_id == other.device_id
    
    def __hash__(self):
        return hash(self.device_id)
    
    def __str__(self):
        return f"{self.name} ({self.mount_point})"

class USBMonitor:
    """Monitors USB devices being connected and disconnected"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.connected_devices = {}  # device_id -> USBDevice
        self.device_added_callbacks = []
        self.device_removed_callbacks = []
        self._lock = threading.Lock()
    
    def register_device_callback(self, device_added_cb=None, device_removed_cb=None):
        """Register callbacks for device events"""
        if device_added_cb:
            self.device_added_callbacks.append(device_added_cb)
        if device_removed_cb:
            self.device_removed_callbacks.append(device_removed_cb)
    
    def _trigger_device_added(self, device):
        """Trigger callbacks when a device is added"""
        for callback in self.device_added_callbacks:
            try:
                callback(device)
            except Exception as e:
                self.logger.error(f"Error in device added callback: {str(e)}")
    
    def _trigger_device_removed(self, device):
        """Trigger callbacks when a device is removed"""
        for callback in self.device_removed_callbacks:
            try:
                callback(device)
            except Exception as e:
                self.logger.error(f"Error in device removed callback: {str(e)}")
    
    def get_connected_devices(self):
        """Get a list of currently connected USB devices"""
        with self._lock:
            return list(self.connected_devices.values())
    
    def is_device_connected(self, device_id):
        """Check if a specific device is connected"""
        with self._lock:
            return device_id in self.connected_devices
    
    def get_device_by_mount_point(self, mount_point):
        """Get device information by mount point"""
        with self._lock:
            for device in self.connected_devices.values():
                if device.mount_point == mount_point:
                    return device
        return None
    
    def start_monitoring(self, stop_event):
        """Start monitoring for USB devices"""
        self.logger.info("Starting USB device monitoring")
        
        # Get initial devices
        current_devices = self._detect_devices()
        with self._lock:
            for device in current_devices:
                self.connected_devices[device.device_id] = device
                self.logger.info(f"Initial USB device detected: {device.name} at {device.mount_point}")
        
        # Create platform-specific monitoring
        if platform.system() == 'Windows':
            self._monitor_windows_devices(stop_event)
        elif platform.system() == 'Linux':
            self._monitor_linux_devices(stop_event)
        elif platform.system() == 'Darwin':  # macOS
            self._monitor_macos_devices(stop_event)
        else:
            self.logger.error(f"Unsupported platform: {platform.system()}")
            self._monitor_fallback(stop_event)
    
    def _detect_devices(self):
        """Detect currently connected USB storage devices"""
        if platform.system() == 'Windows':
            return self._detect_windows_devices()
        elif platform.system() == 'Linux':
            return self._detect_linux_devices()
        elif platform.system() == 'Darwin':  # macOS
            return self._detect_macos_devices()
        else:
            self.logger.warning(f"USB detection not fully supported on {platform.system()}")
            return []
    
    def _detect_windows_devices(self):
        """Detect USB storage devices on Windows"""
        devices = []
        try:
            wmi_obj = wmi.WMI()
            
            # Get logical disks (drive letters)
            for disk in wmi_obj.Win32_LogicalDisk(DriveType=2):  # DriveType=2 for removable drives
                try:
                    # Get physical disk information
                    for partition in wmi_obj.Win32_DiskDriveToDiskPartition():
                        if partition.Dependent.DeviceID == disk.DeviceID.replace(":", ""):
                            disk_drive = wmi_obj.Win32_DiskDrive(DeviceID=partition.Antecedent.DeviceID)[0]
                            
                            if 'USB' in disk_drive.InterfaceType:
                                device = USBDevice(
                                    device_id=disk_drive.PNPDeviceID,
                                    name=disk.VolumeName or f"Removable Disk ({disk.DeviceID})",
                                    mount_point=f"{disk.DeviceID}\\",
                                    serial=disk_drive.SerialNumber.strip() if disk_drive.SerialNumber else None,
                                    vendor=disk_drive.Manufacturer,
                                    model=disk_drive.Model
                                )
                                devices.append(device)
                except Exception as e:
                    self.logger.error(f"Error getting disk information: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error detecting Windows USB devices: {str(e)}")
        
        return devices
    
    def _detect_linux_devices(self):
        """Detect USB storage devices on Linux"""
        devices = []
        try:
            context = pyudev.Context()
            
            for device in context.list_devices(subsystem='block', DEVTYPE='partition'):
                if device.get('ID_BUS') == 'usb' or device.find_parent(subsystem='usb'):
                    # Check if mounted
                    mount_point = None
                    
                    # Read /proc/mounts to find mount points
                    with open('/proc/mounts', 'r') as f:
                        for line in f:
                            parts = line.split()
                            if len(parts) > 1 and parts[0] == device.device_node:
                                mount_point = parts[1]
                                break
                    
                    if mount_point:
                        # Get device details
                        vendor = device.get('ID_VENDOR') or device.get('ID_VENDOR_ID', 'Unknown')
                        model = device.get('ID_MODEL') or device.get('ID_MODEL_ID', 'USB Storage')
                        serial = device.get('ID_SERIAL_SHORT', None)
                        
                        device_obj = USBDevice(
                            device_id=device.get('ID_SERIAL', device.device_node),
                            name=model,
                            mount_point=mount_point,
                            serial=serial,
                            vendor=vendor,
                            model=model
                        )
                        devices.append(device_obj)
        
        except Exception as e:
            self.logger.error(f"Error detecting Linux USB devices: {str(e)}")
        
        return devices
    
    def _detect_macos_devices(self):
        """Detect USB storage devices on macOS"""
        devices = []
        try:
            # Use diskutil to list all external volumes
            result = subprocess.run(['diskutil', 'list', '-plist', 'external'], 
                                   capture_output=True, text=False)
            
            if result.returncode == 0:
                disk_list = plistlib.loads(result.stdout)
                
                for disk_id in disk_list.get('AllDisksAndPartitions', []):
                    # Get detailed info about this disk
                    disk_info = subprocess.run(['diskutil', 'info', '-plist', disk_id.get('DeviceIdentifier', '')],
                                              capture_output=True, text=False)
                    
                    if disk_info.returncode == 0:
                        info = plistlib.loads(disk_info.stdout)
                        
                        # Check if it's a USB device
                        if info.get('BusProtocol') == 'USB':
                            mount_point = info.get('MountPoint')
                            
                            if mount_point:
                                device = USBDevice(
                                    device_id=info.get('DeviceIdentifier'),
                                    name=info.get('VolumeName', 'USB Volume'),
                                    mount_point=mount_point,
                                    serial=info.get('IORegistryEntrySerial'),
                                    vendor=info.get('MediaName', 'Unknown'),
                                    model=info.get('MediaType', 'USB Storage')
                                )
                                devices.append(device)
        
        except Exception as e:
            self.logger.error(f"Error detecting macOS USB devices: {str(e)}")
        
        return devices
    
    def _monitor_windows_devices(self, stop_event):
        """Monitor USB devices on Windows"""
        self.logger.info("Starting Windows USB monitor")
        
        while not stop_event.is_set():
            try:
                current_devices = self._detect_windows_devices()
                current_device_ids = {device.device_id for device in current_devices}
                
                with self._lock:
                    # Check for removed devices
                    for device_id in list(self.connected_devices.keys()):
                        if device_id not in current_device_ids:
                            removed_device = self.connected_devices.pop(device_id)
                            self.logger.info(f"USB device removed: {removed_device.name} from {removed_device.mount_point}")
                            self._trigger_device_removed(removed_device)
                    
                    # Check for new devices
                    for device in current_devices:
                        if device.device_id not in self.connected_devices:
                            self.connected_devices[device.device_id] = device
                            self.logger.info(f"New USB device detected: {device.name} at {device.mount_point}")
                            self._trigger_device_added(device)
            
            except Exception as e:
                self.logger.error(f"Error in Windows USB monitoring: {str(e)}")
            
            # Sleep before next check
            time.sleep(1)
    
    def _monitor_linux_devices(self, stop_event):
        """Monitor USB devices on Linux using pyudev"""
        self.logger.info("Starting Linux USB monitor")
        
        try:
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem='block', device_type='partition')
            
            # Start the monitor
            monitor.start()
            
            for device in iter(lambda: monitor.poll(1), None):
                if stop_event.is_set():
                    break
                
                try:
                    if device.action == 'add' and (device.get('ID_BUS') == 'usb' or device.find_parent(subsystem='usb')):
                        # Wait a moment for the device to be properly mounted
                        time.sleep(1)
                        
                        # Find mount point
                        mount_point = None
                        with open('/proc/mounts', 'r') as f:
                            for line in f:
                                parts = line.split()
                                if len(parts) > 1 and parts[0] == device.device_node:
                                    mount_point = parts[1]
                                    break
                        
                        if mount_point:
                            vendor = device.get('ID_VENDOR') or device.get('ID_VENDOR_ID', 'Unknown')
                            model = device.get('ID_MODEL') or device.get('ID_MODEL_ID', 'USB Storage')
                            serial = device.get('ID_SERIAL_SHORT', None)
                            
                            new_device = USBDevice(
                                device_id=device.get('ID_SERIAL', device.device_node),
                                name=model,
                                mount_point=mount_point,
                                serial=serial,
                                vendor=vendor,
                                model=model
                            )
                            
                            with self._lock:
                                self.connected_devices[new_device.device_id] = new_device
                            
                            self.logger.info(f"New USB device detected: {new_device.name} at {new_device.mount_point}")
                            self._trigger_device_added(new_device)
                    
                    elif device.action == 'remove' and (device.get('ID_BUS') == 'usb' or device.find_parent(subsystem='usb')):
                        device_id = device.get('ID_SERIAL', device.device_node)
                        
                        with self._lock:
                            if device_id in self.connected_devices:
                                removed_device = self.connected_devices.pop(device_id)
                                self.logger.info(f"USB device removed: {removed_device.name} from {removed_device.mount_point}")
                                self._trigger_device_removed(removed_device)
                
                except Exception as e:
                    self.logger.error(f"Error processing Linux device event: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error in Linux USB monitoring: {str(e)}")
            # Fall back to polling
            self._monitor_fallback(stop_event)
    
    def _monitor_macos_devices(self, stop_event):
        """Monitor USB devices on macOS"""
        self.logger.info("Starting macOS USB monitor")
        
        # macOS doesn't have a simple API for direct monitoring, so we poll
        self._monitor_fallback(stop_event)
    
    def _monitor_fallback(self, stop_event):
        """Fallback polling monitor for all platforms"""
        self.logger.info("Starting fallback USB monitor (polling)")
        
        while not stop_event.is_set():
            try:
                current_devices = self._detect_devices()
                current_device_ids = {device.device_id for device in current_devices}
                
                with self._lock:
                    # Check for removed devices
                    for device_id in list(self.connected_devices.keys()):
                        if device_id not in current_device_ids:
                            removed_device = self.connected_devices.pop(device_id)
                            self.logger.info(f"USB device removed: {removed_device.name} from {removed_device.mount_point}")
                            self._trigger_device_removed(removed_device)
                    
                    # Check for new devices
                    for device in current_devices:
                        if device.device_id not in self.connected_devices:
                            self.connected_devices[device.device_id] = device
                            self.logger.info(f"New USB device detected: {device.name} at {device.mount_point}")
                            self._trigger_device_added(device)
            
            except Exception as e:
                self.logger.error(f"Error in fallback USB monitoring: {str(e)}")
            
            # Sleep before next check
            time.sleep(2)