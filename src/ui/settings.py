"""
Settings dialog for configuring the USB File Transfer Tracker
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

class SettingsDialog:
    """Settings dialog window for the application"""
    
    def __init__(self, config, logger, parent=None):
        self.config = config
        self.logger = logger
        self.result = False
        
        # Create dialog window
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("USB File Transfer Tracker Settings")
        self.root.geometry("600x500")
        self.root.minsize(500, 400)
        self.root.resizable(True, True)
        
        # Make dialog modal
        if parent:
            self.root.transient(parent)
            self.root.grab_set()
        
        # Create widgets
        self._create_notebook()
        self._create_buttons()
        
        # Load current settings
        self._load_settings()
        
        # Center the dialog
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_notebook(self):
        """Create tabbed notebook for settings categories"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.general_tab = ttk.Frame(self.notebook)
        self.monitoring_tab = ttk.Frame(self.notebook)
        self.alerts_tab = ttk.Frame(self.notebook)
        self.security_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.general_tab, text="General")
        self.notebook.add(self.monitoring_tab, text="Monitoring")
        self.notebook.add(self.alerts_tab, text="Alerts")
        self.notebook.add(self.security_tab, text="Security")
        
        # Create widgets for each tab
        self._create_general_tab()
        self._create_monitoring_tab()
        self._create_alerts_tab()
        self._create_security_tab()
    
    def _create_general_tab(self):
        """Create general settings tab"""
        frame = ttk.Frame(self.general_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Log directory
        ttk.Label(frame, text="Log Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        log_frame = ttk.Frame(frame)
        log_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        self.log_dir_var = tk.StringVar()
        log_entry = ttk.Entry(log_frame, textvariable=self.log_dir_var, width=40)
        log_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        log_browse = ttk.Button(log_frame, text="Browse...", command=self._browse_log_dir)
        log_browse.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Run at startup
        self.startup_var = tk.BooleanVar()
        startup_check = ttk.Checkbutton(frame, text="Run at system startup", variable=self.startup_var)
        startup_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Minimize to tray
        self.tray_var = tk.BooleanVar()
        tray_check = ttk.Checkbutton(frame, text="Minimize to system tray", variable=self.tray_var)
        tray_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Make column expandable
        frame.columnconfigure(1, weight=1)
    
    def _create_monitoring_tab(self):
        """Create monitoring settings tab"""
        frame = ttk.Frame(self.monitoring_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Check interval
        ttk.Label(frame, text="Check Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.StringVar()
        interval_entry = ttk.Entry(frame, textvariable=self.interval_var, width=5)
        interval_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Included file extensions
        ttk.Label(frame, text="Included File Extensions:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.include_var = tk.StringVar()
        include_entry = ttk.Entry(frame, textvariable=self.include_var, width=40)
        include_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)
        ttk.Label(frame, text="Comma-separated, use * for all").grid(row=2, column=1, sticky=tk.W)
        
        # Excluded file extensions
        ttk.Label(frame, text="Excluded File Extensions:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.exclude_var = tk.StringVar()
        exclude_entry = ttk.Entry(frame, textvariable=self.exclude_var, width=40)
        exclude_entry.grid(row=3, column=1, sticky=tk.EW, pady=5)
        ttk.Label(frame, text="Comma-separated, e.g. .tmp,.temp").grid(row=4, column=1, sticky=tk.W)
        
        # Min/Max file size
        ttk.Label(frame, text="Minimum File Size (bytes):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.min_size_var = tk.StringVar()
        min_size_entry = ttk.Entry(frame, textvariable=self.min_size_var, width=10)
        min_size_entry.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Maximum File Size (bytes):").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.max_size_var = tk.StringVar()
        max_size_entry = ttk.Entry(frame, textvariable=self.max_size_var, width=10)
        max_size_entry.grid(row=6, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Leave empty for no limit").grid(row=7, column=1, sticky=tk.W)
        
        # Make column expandable
        frame.columnconfigure(1, weight=1)
    
    def _create_alerts_tab(self):
        """Create alerts settings tab"""
        frame = ttk.Frame(self.alerts_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Enable alerts
        self.alerts_enabled_var = tk.BooleanVar()
        alerts_check = ttk.Checkbutton(frame, text="Enable Alerts", variable=self.alerts_enabled_var)
        alerts_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Alert threshold
        ttk.Label(frame, text="Alert Threshold (MB):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.StringVar()
        threshold_entry = ttk.Entry(frame, textvariable=self.threshold_var, width=5)
        threshold_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Suspicious extensions
        ttk.Label(frame, text="Suspicious Extensions:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.suspicious_var = tk.StringVar()
        suspicious_entry = ttk.Entry(frame, textvariable=self.suspicious_var, width=40)
        suspicious_entry.grid(row=2, column=1, sticky=tk.EW, pady=5)
        ttk.Label(frame, text="Comma-separated, e.g. .zip,.exe").grid(row=3, column=1, sticky=tk.W)
        
        # Large transfer alert
        self.large_transfer_var = tk.BooleanVar()
        large_check = ttk.Checkbutton(frame, text="Alert on Large Transfers", variable=self.large_transfer_var)
        large_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Large Transfer Size (MB):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.large_size_var = tk.StringVar()
        large_size_entry = ttk.Entry(frame, textvariable=self.large_size_var, width=5)
        large_size_entry.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Time-based alerts
        ttk.Label(frame, text="Time-Based Alerts:").grid(row=6, column=0, sticky=tk.W, pady=(15, 5))
        
        self.time_alerts_var = tk.BooleanVar()
        time_check = ttk.Checkbutton(frame, text="Enable Time-Based Alerts", variable=self.time_alerts_var)
        time_check.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Restricted Hours:").grid(row=8, column=0, sticky=tk.W, pady=5)
        time_frame = ttk.Frame(frame)
        time_frame.grid(row=8, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(time_frame, text="From:").pack(side=tk.LEFT)
        self.time_start_var = tk.StringVar()
        time_start_entry = ttk.Entry(time_frame, textvariable=self.time_start_var, width=5)
        time_start_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(time_frame, text="To:").pack(side=tk.LEFT, padx=(10, 0))
        self.time_end_var = tk.StringVar()
        time_end_entry = ttk.Entry(time_frame, textvariable=self.time_end_var, width=5)
        time_end_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(time_frame, text="(24-hour format, e.g. 18:00)").pack(side=tk.LEFT, padx=(10, 0))
        
        self.weekend_alerts_var = tk.BooleanVar()
        weekend_check = ttk.Checkbutton(frame, text="Alert on Weekend Activity", variable=self.weekend_alerts_var)
        weekend_check.grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Make column expandable
        frame.columnconfigure(1, weight=1)
    
    def _create_security_tab(self):
        """Create security settings tab"""
        frame = ttk.Frame(self.security_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Hash algorithm
        ttk.Label(frame, text="Hash Algorithm:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.hash_var = tk.StringVar()
        hash_combo = ttk.Combobox(frame, textvariable=self.hash_var, 
                                   values=["sha256", "sha512", "md5"], width=10)
        hash_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Encrypt logs
        self.encrypt_var = tk.BooleanVar()
        encrypt_check = ttk.Checkbutton(frame, text="Encrypt Log Files", variable=self.encrypt_var)
        encrypt_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Log retention
        ttk.Label(frame, text="Log Retention (days):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.retention_var = tk.StringVar()
        retention_entry = ttk.Entry(frame, textvariable=self.retention_var, width=5)
        retention_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Make column expandable
        frame.columnconfigure(1, weight=1)
    
    def _create_buttons(self):
        """Create action buttons"""
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        save_button = ttk.Button(button_frame, text="Save", command=self._save_settings)
        save_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel)
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def _load_settings(self):
        """Load current settings into the UI"""
        # General settings
        self.log_dir_var.set(self.config.general.log_directory)
        self.startup_var.set(self.config.general.run_at_startup)
        self.tray_var.set(self.config.general.minimize_to_tray)
        
        # Monitoring settings
        self.interval_var.set(str(self.config.monitoring.check_interval_seconds))
        self.include_var.set(",".join(self.config.monitoring.include_file_extensions))
        self.exclude_var.set(",".join(self.config.monitoring.exclude_file_extensions))
        self.min_size_var.set(str(self.config.monitoring.min_file_size_bytes))
        self.max_size_var.set("" if self.config.monitoring.max_file_size_bytes is None 
                            else str(self.config.monitoring.max_file_size_bytes))
        
        # Alert settings
        self.alerts_enabled_var.set(self.config.alerts.enable_alerts)
        self.threshold_var.set(str(self.config.alerts.alert_threshold_mb))
        self.suspicious_var.set(",".join(self.config.alerts.suspicious_extensions))
        self.large_transfer_var.set(self.config.alerts.large_transfer_alert)
        self.large_size_var.set(str(self.config.alerts.large_transfer_threshold_mb))
        
        # Time-based alerts
        self.time_alerts_var.set(self.config.alerts.time_based_alerts.enabled)
        self.time_start_var.set(self.config.alerts.time_based_alerts.restricted_hours["start"])
        self.time_end_var.set(self.config.alerts.time_based_alerts.restricted_hours["end"])
        self.weekend_alerts_var.set(self.config.alerts.time_based_alerts.weekend_alerts)
        
        # Security settings
        self.hash_var.set(self.config.security.hash_algorithm)
        self.encrypt_var.set(self.config.security.encrypt_logs)
        self.retention_var.set(str(self.config.security.log_retention_days))
    
    def _save_settings(self):
        """Save settings from the UI to the config"""
        try:
            # Validate inputs
            try:
                check_interval = int(self.interval_var.get())
                if check_interval < 1:
                    raise ValueError("Check interval must be at least 1 second")
            except ValueError:
                messagebox.showerror("Invalid Value", "Check interval must be a positive integer")
                self.notebook.select(1)  # Switch to monitoring tab
                return
            
            try:
                min_size = int(self.min_size_var.get())
                if min_size < 0:
                    raise ValueError("Minimum file size cannot be negative")
            except ValueError:
                messagebox.showerror("Invalid Value", "Minimum file size must be a non-negative integer")
                self.notebook.select(1)  # Switch to monitoring tab
                return
            
            max_size_str = self.max_size_var.get().strip()
            max_size = None
            if max_size_str:
                try:
                    max_size = int(max_size_str)
                    if max_size < min_size:
                        raise ValueError("Maximum file size must be greater than minimum file size")
                except ValueError:
                    messagebox.showerror("Invalid Value", "Maximum file size must be a valid integer greater than minimum size")
                    self.notebook.select(1)  # Switch to monitoring tab
                    return
            
            try:
                threshold = int(self.threshold_var.get())
                if threshold < 0:
                    raise ValueError("Alert threshold cannot be negative")
            except ValueError:
                messagebox.showerror("Invalid Value", "Alert threshold must be a non-negative integer")
                self.notebook.select(2)  # Switch to alerts tab
                return
            
            try:
                large_size = int(self.large_size_var.get())
                if large_size < 0:
                    raise ValueError("Large transfer threshold cannot be negative")
            except ValueError:
                messagebox.showerror("Invalid Value", "Large transfer threshold must be a non-negative integer")
                self.notebook.select(2)  # Switch to alerts tab
                return
            
            try:
                retention = int(self.retention_var.get())
                if retention < 1:
                    raise ValueError("Log retention must be at least 1 day")
            except ValueError:
                messagebox.showerror("Invalid Value", "Log retention must be a positive integer")
                self.notebook.select(3)  # Switch to security tab
                return
            
            # Update general settings
            self.config.general.log_directory = self.log_dir_var.get()
            self.config.general.run_at_startup = self.startup_var.get()
            self.config.general.minimize_to_tray = self.tray_var.get()
            
            # Update monitoring settings
            self.config.monitoring.check_interval_seconds = check_interval
            self.config.monitoring.include_file_extensions = [ext.strip() for ext in self.include_var.get().split(",") if ext.strip()]
            self.config.monitoring.exclude_file_extensions = [ext.strip() for ext in self.exclude_var.get().split(",") if ext.strip()]
            self.config.monitoring.min_file_size_bytes = min_size
            self.config.monitoring.max_file_size_bytes = max_size
            
            # Update alert settings
            self.config.alerts.enable_alerts = self.alerts_enabled_var.get()
            self.config.alerts.alert_threshold_mb = threshold
            self.config.alerts.suspicious_extensions = [ext.strip() for ext in self.suspicious_var.get().split(",") if ext.strip()]
            self.config.alerts.large_transfer_alert = self.large_transfer_var.get()
            self.config.alerts.large_transfer_threshold_mb = large_size
            
            # Update time-based alerts
            self.config.alerts.time_based_alerts.enabled = self.time_alerts_var.get()
            self.config.alerts.time_based_alerts.restricted_hours = {
                "start": self.time_start_var.get(),
                "end": self.time_end_var.get()
            }
            self.config.alerts.time_based_alerts.weekend_alerts = self.weekend_alerts_var.get()
            
            # Update security settings
            self.config.security.hash_algorithm = self.hash_var.get()
            self.config.security.encrypt_logs = self.encrypt_var.get()
            self.config.security.log_retention_days = retention
            
            # Create log directory if it doesn't exist
            log_dir = Path(self.config.general.log_directory)
            log_dir.mkdir(exist_ok=True, parents=True)
            
            self.result = True
            self.root.destroy()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def _cancel(self):
        """Cancel settings changes"""
        self.result = False
        self.root.destroy()
    
    def _browse_log_dir(self):
        """Browse for log directory"""
        current_dir = self.log_dir_var.get()
        if not os.path.isdir(current_dir):
            current_dir = os.path.dirname(current_dir) if current_dir else os.getcwd()
        
        directory = filedialog.askdirectory(initialdir=current_dir, title="Select Log Directory")
        if directory:
            self.log_dir_var.set(directory)
    
    def run(self):
        """Run the dialog and return whether settings were saved"""
        self.root.mainloop()
        return self.result

def open_settings(config, logger):
    """Open the settings dialog and return whether settings were saved"""
    dialog = SettingsDialog(config, logger)
    return dialog.run()