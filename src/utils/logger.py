"""
Logging utilities for the USB File Transfer Tracker
"""

import os
import sys
import time
import logging
import hashlib
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

class SecureFileHandler(RotatingFileHandler):
    """A file handler that adds a hash to each log file for tamper detection"""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.hash_file = f"{filename}.hash"
        self.current_hash = None
        
    def _compute_file_hash(self):
        """Compute SHA-256 hash of the log file"""
        if not os.path.exists(self.baseFilename):
            return None
            
        sha256 = hashlib.sha256()
        with open(self.baseFilename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _save_hash(self):
        """Save the current hash to the hash file"""
        self.current_hash = self._compute_file_hash()
        if self.current_hash:
            with open(self.hash_file, 'w') as f:
                f.write(self.current_hash)
    
    def _check_hash(self):
        """Check if the current file hash matches the saved hash"""
        if not os.path.exists(self.hash_file):
            return True
            
        with open(self.hash_file, 'r') as f:
            saved_hash = f.read().strip()
        
        current_hash = self._compute_file_hash()
        return saved_hash == current_hash
    
    def emit(self, record):
        """Emit a record and update the hash file"""
        super().emit(record)
        self._save_hash()
    
    def doRollover(self):
        """Perform a rollover and update hash files"""
        super().doRollover()
        self._save_hash()

def setup_logger(log_directory="logs"):
    """Set up and configure the application logger"""
    # Create logs directory if it doesn't exist
    log_dir = Path(log_directory)
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Configure application logger
    app_logger = logging.getLogger('usb_tracker')
    app_logger.setLevel(logging.DEBUG)
    
    # Create formatter for detailed logs
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    
    # Create application log file handler (daily rotation)
    today = datetime.now().strftime('%Y-%m-%d')
    app_log_file = log_dir / f"app_{today}.log"
    app_file_handler = SecureFileHandler(
        filename=str(app_log_file),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=10
    )
    app_file_handler.setLevel(logging.DEBUG)
    app_file_handler.setFormatter(detailed_formatter)
    
    # Add handlers to the logger
    app_logger.addHandler(console_handler)
    app_logger.addHandler(app_file_handler)
    
    # Create transfer logger (separate from application logger)
    transfer_logger = logging.getLogger('transfer_log')
    transfer_logger.setLevel(logging.INFO)
    
    # Create formatter for transfer logs (CSV format)
    transfer_formatter = logging.Formatter('%(asctime)s,%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # Create transfer log file handler
    transfer_log_file = log_dir / f"transfers_{today}.csv"
    
    # Create header if file doesn't exist
    if not transfer_log_file.exists():
        with open(transfer_log_file, 'w') as f:
            f.write("timestamp,operation,device,file_path,file_size,file_type,user\n")
    
    transfer_file_handler = SecureFileHandler(
        filename=str(transfer_log_file),
        maxBytes=50*1024*1024,  # 50 MB
        backupCount=20
    )
    transfer_file_handler.setLevel(logging.INFO)
    transfer_file_handler.setFormatter(transfer_formatter)
    
    # Add handler to the transfer logger
    transfer_logger.addHandler(transfer_file_handler)
    
    # Function to clean up old log files
    def cleanup_old_logs(log_dir, days_to_keep=90):
        """Delete log files older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        for log_file in log_dir.glob("*.log*"):
            try:
                file_date_str = log_file.name.split('_')[1].split('.')[0]
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if file_date < cutoff_date:
                    log_file.unlink()
                    # Also remove the hash file if it exists
                    hash_file = Path(f"{log_file}.hash")
                    if hash_file.exists():
                        hash_file.unlink()
            except (IndexError, ValueError):
                # Skip files that don't match the expected pattern
                continue
    
    # Run log cleanup
    cleanup_old_logs(log_dir)
    
    return app_logger


def log_file_transfer(logger, operation, device, file_path, file_size, file_type, user):
    """Log a file transfer operation"""
    transfer_logger = logging.getLogger('transfer_log')
    message = f"{operation},{device},{file_path},{file_size},{file_type},{user}"
    transfer_logger.info(message)
    
    # Also log to application logger
    logger.info(f"File {operation}: {file_path} ({file_size} bytes) to/from {device} by {user}")


def verify_log_integrity(log_file):
    """Verify the integrity of a log file using its hash"""
    hash_file = f"{log_file}.hash"
    
    if not os.path.exists(hash_file):
        return False, "Hash file missing"
    
    # Read saved hash
    with open(hash_file, 'r') as f:
        saved_hash = f.read().strip()
    
    # Compute current hash
    sha256 = hashlib.sha256()
    with open(log_file, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    current_hash = sha256.hexdigest()
    
    if saved_hash != current_hash:
        return False, "Hash mismatch, log file may have been tampered with"
    
    return True, "Log file integrity verified"