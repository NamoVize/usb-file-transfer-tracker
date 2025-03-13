"""
File watcher module for monitoring file operations on USB drives.
Uses watchdog to track file system events.
"""

import os
import re
import time
import fnmatch
import getpass
import threading
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils.logger import log_file_transfer

class USBFileEventHandler(FileSystemEventHandler):
    """File system event handler for USB drives"""
    
    def __init__(self, config, logger, usb_monitor, device):
        self.config = config
        self.logger = logger
        self.usb_monitor = usb_monitor
        self.device = device
        self.username = getpass.getuser()
        
        # Track file operations in progress
        self._operations_lock = threading.Lock()
        self._in_progress = {}  # path -> (operation, start_time)
        
        # Time threshold for considering operations complete (seconds)
        self.op_completion_time = 1.0
        
        # Start operation finalizer thread
        self.stop_event = threading.Event()
        self.finalizer_thread = threading.Thread(
            target=self._finalize_operations,
            name=f"Finalizer-{device.name}",
            daemon=True
        )
        self.finalizer_thread.start()
    
    def stop(self):
        """Stop the finalizer thread"""
        self.stop_event.set()
        self.finalizer_thread.join(timeout=2)
    
    def _should_monitor_file(self, path):
        """Determine if a file should be monitored based on config rules"""
        if not os.path.isfile(path):
            return False
            
        # Check file size constraints
        try:
            size_bytes = os.path.getsize(path)
            if self.config.monitoring.min_file_size_bytes > 0 and size_bytes < self.config.monitoring.min_file_size_bytes:
                return False
                
            if self.config.monitoring.max_file_size_bytes and size_bytes > self.config.monitoring.max_file_size_bytes:
                return False
        except:
            # If we can't get the size, assume we should monitor
            pass
            
        # Get file extension
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        
        # Check inclusion/exclusion patterns
        include_patterns = self.config.monitoring.include_file_extensions
        exclude_patterns = self.config.monitoring.exclude_file_extensions
        
        # If include patterns contains only "*", monitor all files except excluded ones
        if len(include_patterns) == 1 and include_patterns[0] == "*":
            return ext not in exclude_patterns
            
        # Otherwise, file must match an include pattern and not match any exclude pattern
        included = False
        for pattern in include_patterns:
            if ext.endswith(pattern) or fnmatch.fnmatch(ext, pattern):
                included = True
                break
                
        if not included:
            return False
            
        for pattern in exclude_patterns:
            if ext.endswith(pattern) or fnmatch.fnmatch(ext, pattern):
                return False
                
        return True
    
    def _is_suspicious_file(self, path):
        """Check if a file might be suspicious based on extension and size"""
        # Get file extension
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        
        # Check if extension is in suspicious list
        if ext in self.config.alerts.suspicious_extensions:
            # Get file size
            try:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                # If file is larger than threshold, it's suspicious
                if size_mb > self.config.alerts.alert_threshold_mb:
                    return True
            except:
                # If we can't get the size, err on the side of caution
                return True
                
        return False
    
    def _check_time_based_alerts(self):
        """Check if current time should trigger time-based alerts"""
        if not self.config.alerts.time_based_alerts.enabled:
            return False
            
        current_time = datetime.now()
        current_hour = current_time.hour
        is_weekend = current_time.weekday() >= 5  # 5 = Saturday, 6 = Sunday
        
        # Check weekend restriction
        if is_weekend and self.config.alerts.time_based_alerts.weekend_alerts:
            return True
            
        # Check time restriction
        start_hour = int(self.config.alerts.time_based_alerts.restricted_hours["start"].split(":")[0])
        end_hour = int(self.config.alerts.time_based_alerts.restricted_hours["end"].split(":")[0])
        
        # Handle overnight ranges (e.g., 18:00 to 07:00)
        if start_hour > end_hour:
            return current_hour >= start_hour or current_hour < end_hour
        else:
            return current_hour >= start_hour and current_hour < end_hour
            
        return False
    
    def _log_file_operation(self, operation, path, final=False):
        """Log a file operation with appropriate alerts if necessary"""
        try:
            relative_path = os.path.relpath(path, self.device.mount_point)
            file_size = os.path.getsize(path) if os.path.exists(path) else 0
            file_type = os.path.splitext(path)[1].lower()
            
            # Check if this is a large file transfer
            is_large_transfer = False
            if self.config.alerts.large_transfer_alert:
                size_mb = file_size / (1024 * 1024)
                if size_mb > self.config.alerts.large_transfer_threshold_mb:
                    is_large_transfer = True
                    self.logger.warning(
                        f"LARGE FILE TRANSFER: {operation} {relative_path} ({size_mb:.2f} MB) "
                        f"on {self.device.name} by {self.username}"
                    )
            
            # Check for suspicious files
            is_suspicious = self._is_suspicious_file(path)
            if is_suspicious:
                self.logger.warning(
                    f"SUSPICIOUS FILE: {operation} {relative_path} ({file_size} bytes) "
                    f"on {self.device.name} by {self.username}"
                )
            
            # Check for time-based alerts
            if self._check_time_based_alerts():
                self.logger.warning(
                    f"AFTER-HOURS ACTIVITY: {operation} {relative_path} ({file_size} bytes) "
                    f"on {self.device.name} by {self.username}"
                )
            
            # Log the transfer
            if final:
                log_file_transfer(
                    self.logger,
                    operation,
                    self.device.name,
                    relative_path,
                    file_size,
                    file_type,
                    self.username
                )
        except Exception as e:
            self.logger.error(f"Error logging file operation: {str(e)}")
    
    def _record_operation(self, operation, path):
        """Record an operation in progress"""
        with self._operations_lock:
            self._in_progress[path] = (operation, time.time())
    
    def _finalize_operations(self):
        """Thread to finalize operations after they're likely complete"""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                to_finalize = []
                
                # Find operations to finalize
                with self._operations_lock:
                    for path, (operation, start_time) in list(self._in_progress.items()):
                        if current_time - start_time > self.op_completion_time:
                            to_finalize.append((path, operation))
                            del self._in_progress[path]
                
                # Finalize operations
                for path, operation in to_finalize:
                    if os.path.exists(path) or operation == "deleted":
                        self._log_file_operation(operation, path, final=True)
            
            except Exception as e:
                self.logger.error(f"Error in operation finalizer: {str(e)}")
                
            time.sleep(0.5)
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and self._should_monitor_file(event.src_path):
            self._record_operation("created", event.src_path)
            self._log_file_operation("created", event.src_path)
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if not event.is_directory:
            # We can't check if it should be monitored since it's gone
            self._record_operation("deleted", event.src_path)
            self._log_file_operation("deleted", event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and self._should_monitor_file(event.src_path):
            self._record_operation("modified", event.src_path)
            self._log_file_operation("modified", event.src_path)
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory:
            # Check both source and destination if applicable
            if hasattr(event, 'dest_path') and self._should_monitor_file(event.dest_path):
                self._record_operation("moved", event.dest_path)
                self._log_file_operation("moved", event.dest_path)
            elif self._should_monitor_file(event.src_path):
                self._record_operation("moved", event.src_path)
                self._log_file_operation("moved", event.src_path)

class FileWatcher:
    """Monitors file operations on connected USB drives"""
    
    def __init__(self, config, logger, usb_monitor):
        self.config = config
        self.logger = logger
        self.usb_monitor = usb_monitor
        
        # Register for USB device callbacks
        self.usb_monitor.register_device_callback(
            device_added_cb=self._handle_device_added,
            device_removed_cb=self._handle_device_removed
        )
        
        # Track observers and handlers
        self._lock = threading.Lock()
        self.observers = {}  # device_id -> Observer
        self.handlers = {}   # device_id -> USBFileEventHandler
    
    def _handle_device_added(self, device):
        """Set up monitoring for a newly added USB device"""
        self.logger.info(f"Setting up file monitoring for {device.name} at {device.mount_point}")
        
        try:
            # Create event handler for this device
            handler = USBFileEventHandler(self.config, self.logger, self.usb_monitor, device)
            
            # Create and start observer
            observer = Observer()
            observer.schedule(handler, device.mount_point, recursive=True)
            observer.start()
            
            # Store references
            with self._lock:
                self.observers[device.device_id] = observer
                self.handlers[device.device_id] = handler
                
            self.logger.info(f"File monitoring active for {device.name}")
        
        except Exception as e:
            self.logger.error(f"Error setting up file monitoring for {device.name}: {str(e)}")
    
    def _handle_device_removed(self, device):
        """Clean up monitoring for a removed USB device"""
        self.logger.info(f"Stopping file monitoring for {device.name}")
        
        try:
            with self._lock:
                # Get observer and handler
                observer = self.observers.pop(device.device_id, None)
                handler = self.handlers.pop(device.device_id, None)
            
            # Stop handler and observer
            if handler:
                handler.stop()
            
            if observer:
                observer.stop()
                observer.join(timeout=2)
                
            self.logger.info(f"File monitoring stopped for {device.name}")
        
        except Exception as e:
            self.logger.error(f"Error stopping file monitoring for {device.name}: {str(e)}")
    
    def start_monitoring(self, stop_event):
        """Start monitoring files on USB devices"""
        self.logger.info("Starting file monitoring service")
        
        # Set up monitoring for already connected devices
        for device in self.usb_monitor.get_connected_devices():
            self._handle_device_added(device)
        
        # Keep thread alive until stop event
        try:
            while not stop_event.is_set():
                time.sleep(1)
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop all file monitoring"""
        self.logger.info("Stopping all file monitoring")
        
        with self._lock:
            # Stop all handlers
            for handler in self.handlers.values():
                try:
                    handler.stop()
                except:
                    pass
            
            # Stop all observers
            for observer in self.observers.values():
                try:
                    observer.stop()
                except:
                    pass
            
            # Join all observers
            for observer in self.observers.values():
                try:
                    observer.join(timeout=2)
                except:
                    pass
            
            # Clear collections
            self.observers.clear()
            self.handlers.clear()
        
        self.logger.info("All file monitoring stopped")