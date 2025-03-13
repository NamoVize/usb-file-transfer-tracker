"""
Log viewer UI for displaying and filtering USB file transfer logs
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from datetime import datetime, timedelta
import threading
from pathlib import Path

from utils.logger import verify_log_integrity

class LogViewer:
    """Log viewer window for displaying and filtering transfer logs"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.log_files = []
        self.current_log_file = None
        self.current_data = None
        
        # Set up the main window
        self.root = tk.Tk()
        self.root.title("USB File Transfer Log Viewer")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)
        
        # Set up grid 
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        
        # Add widgets
        self._create_toolbar()
        self._create_table()
        self._create_status_bar()
        
        # Load logs
        self._scan_logs()
    
    def _create_toolbar(self):
        """Create toolbar with controls"""
        toolbar = ttk.Frame(self.root)
        toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # File selection
        ttk.Label(toolbar, text="Log file:").pack(side=tk.LEFT, padx=(0, 5))
        self.file_combo = ttk.Combobox(toolbar, width=40)
        self.file_combo.pack(side=tk.LEFT, padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)
        
        # Filtering
        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(toolbar, textvariable=self.filter_var, width=20)
        filter_entry.pack(side=tk.LEFT, padx=5)
        filter_entry.bind("<Return>", self._apply_filter)
        
        # Filter type
        ttk.Label(toolbar, text="Filter by:").pack(side=tk.LEFT, padx=(10, 5))
        self.filter_type = ttk.Combobox(toolbar, values=["Device", "File Name", "Operation", "User"], width=10)
        self.filter_type.current(0)
        self.filter_type.pack(side=tk.LEFT, padx=5)
        
        # Filter button
        filter_btn = ttk.Button(toolbar, text="Apply", command=self._apply_filter)
        filter_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear filter button
        clear_btn = ttk.Button(toolbar, text="Clear", command=self._clear_filter)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Export button
        export_btn = ttk.Button(toolbar, text="Export", command=self._export_logs)
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        # Refresh button
        refresh_btn = ttk.Button(toolbar, text="Refresh", command=self._scan_logs)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Verify button 
        verify_btn = ttk.Button(toolbar, text="Verify Integrity", command=self._verify_integrity)
        verify_btn.pack(side=tk.RIGHT, padx=5)
    
    def _create_table(self):
        """Create the main table for displaying logs"""
        # Create frame for table + scrollbars
        table_frame = ttk.Frame(self.root)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Create treeview for data
        columns = ("timestamp", "operation", "device", "file_path", "file_size", "file_type", "user")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Set column headings
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("operation", text="Operation")
        self.tree.heading("device", text="Device")
        self.tree.heading("file_path", text="File Path")
        self.tree.heading("file_size", text="Size (bytes)")
        self.tree.heading("file_type", text="File Type")
        self.tree.heading("user", text="User")
        
        # Set column widths
        self.tree.column("timestamp", width=150)
        self.tree.column("operation", width=80)
        self.tree.column("device", width=120)
        self.tree.column("file_path", width=300)
        self.tree.column("file_size", width=80)
        self.tree.column("file_type", width=80)
        self.tree.column("user", width=100)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid everything
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Bind events
        self.tree.bind("<Double-1>", self._on_row_double_clicked)
    
    def _create_status_bar(self):
        """Create status bar for information"""
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
        
        self.status_var = tk.StringVar()
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(side=tk.LEFT, fill=tk.X)
        
        self.record_count_var = tk.StringVar()
        record_count_label = ttk.Label(status_frame, textvariable=self.record_count_var, anchor=tk.E)
        record_count_label.pack(side=tk.RIGHT)
        
        self.status_var.set("Ready")
        self.record_count_var.set("0 records")
    
    def _scan_logs(self):
        """Scan the logs directory for log files"""
        self.status_var.set("Scanning for log files...")
        
        log_dir = Path(self.config.general.log_directory)
        if not log_dir.exists():
            self.status_var.set(f"Log directory not found: {log_dir}")
            return
        
        # Find all CSV files
        self.log_files = sorted(list(log_dir.glob("transfers_*.csv")), reverse=True)
        
        # Update combobox
        self.file_combo['values'] = [f.name for f in self.log_files]
        
        if self.log_files:
            self.file_combo.current(0)
            self._load_log_file(self.log_files[0])
        else:
            self.status_var.set("No log files found")
    
    def _load_log_file(self, log_file):
        """Load a log file and display its contents"""
        self.status_var.set(f"Loading {log_file.name}...")
        self.current_log_file = log_file
        
        try:
            # Load CSV file
            self.current_data = pd.read_csv(log_file)
            
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Add data to treeview
            for idx, row in self.current_data.iterrows():
                values = (
                    row.get('timestamp', ''),
                    row.get('operation', ''),
                    row.get('device', ''),
                    row.get('file_path', ''),
                    row.get('file_size', 0),
                    row.get('file_type', ''),
                    row.get('user', '')
                )
                self.tree.insert("", "end", values=values)
            
            # Update status
            self.status_var.set(f"Loaded {log_file.name}")
            self.record_count_var.set(f"{len(self.current_data)} records")
        
        except Exception as e:
            self.status_var.set(f"Error loading file: {str(e)}")
            messagebox.showerror("Error", f"Failed to load log file: {str(e)}")
    
    def _on_file_selected(self, event):
        """Handle file selection from combobox"""
        selection = self.file_combo.current()
        if 0 <= selection < len(self.log_files):
            self._load_log_file(self.log_files[selection])
    
    def _apply_filter(self, event=None):
        """Apply filter to currently loaded data"""
        if self.current_data is None:
            return
        
        filter_text = self.filter_var.get().strip().lower()
        if not filter_text:
            # If no filter, show all data
            self._clear_filter()
            return
        
        filter_type = self.filter_type.get()
        column_map = {
            "Device": "device",
            "File Name": "file_path",
            "Operation": "operation",
            "User": "user"
        }
        
        column = column_map.get(filter_type, "device")
        
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Apply filter
        filtered_data = self.current_data[self.current_data[column].str.lower().str.contains(filter_text, na=False)]
        
        # Add filtered data
        for idx, row in filtered_data.iterrows():
            values = (
                row.get('timestamp', ''),
                row.get('operation', ''),
                row.get('device', ''),
                row.get('file_path', ''),
                row.get('file_size', 0),
                row.get('file_type', ''),
                row.get('user', '')
            )
            self.tree.insert("", "end", values=values)
        
        # Update status
        self.status_var.set(f"Filter applied: {filter_type}='{filter_text}'")
        self.record_count_var.set(f"{len(filtered_data)} records")
    
    def _clear_filter(self):
        """Clear filter and show all data"""
        if self.current_data is None:
            return
        
        self.filter_var.set("")
        
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add all data
        for idx, row in self.current_data.iterrows():
            values = (
                row.get('timestamp', ''),
                row.get('operation', ''),
                row.get('device', ''),
                row.get('file_path', ''),
                row.get('file_size', 0),
                row.get('file_type', ''),
                row.get('user', '')
            )
            self.tree.insert("", "end", values=values)
        
        # Update status
        self.status_var.set("Filter cleared")
        self.record_count_var.set(f"{len(self.current_data)} records")
    
    def _on_row_double_clicked(self, event):
        """Handle double-click on a row to show details"""
        item = self.tree.focus()
        if not item:
            return
        
        values = self.tree.item(item, "values")
        details = "\n".join([f"{col}: {val}" for col, val in zip(self.tree.cget("columns"), values)])
        
        messagebox.showinfo("Transfer Details", details)
    
    def _export_logs(self):
        """Export current view to a CSV file"""
        if self.current_data is None:
            messagebox.showwarning("No Data", "No data to export")
            return
        
        # Get all visible items
        visible_items = self.tree.get_children()
        if not visible_items:
            messagebox.showwarning("No Data", "No visible data to export")
            return
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Log Data"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Get visible data
            visible_data = []
            columns = self.tree.cget("columns")
            
            for item in visible_items:
                values = self.tree.item(item, "values")
                row_dict = {col: val for col, val in zip(columns, values)}
                visible_data.append(row_dict)
            
            # Convert to DataFrame and save
            df = pd.DataFrame(visible_data)
            df.to_csv(file_path, index=False)
            
            self.status_var.set(f"Exported {len(visible_data)} records to {os.path.basename(file_path)}")
            messagebox.showinfo("Export Successful", f"Successfully exported {len(visible_data)} records to {file_path}")
        
        except Exception as e:
            self.status_var.set(f"Export error: {str(e)}")
            messagebox.showerror("Export Failed", f"Failed to export data: {str(e)}")
    
    def _verify_integrity(self):
        """Verify the integrity of the current log file"""
        if self.current_log_file is None:
            messagebox.showwarning("No File", "No log file is currently loaded")
            return
        
        self.status_var.set(f"Verifying integrity of {self.current_log_file.name}...")
        
        def verify_thread():
            try:
                result, message = verify_log_integrity(str(self.current_log_file))
                
                if result:
                    self.root.after(0, lambda: messagebox.showinfo("Verification Successful", 
                                                              f"Log file integrity verified: {message}"))
                    self.root.after(0, lambda: self.status_var.set("Integrity verification passed"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("Verification Failed", 
                                                                 f"Log file may be tampered with: {message}"))
                    self.root.after(0, lambda: self.status_var.set("Integrity verification failed"))
            
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Verification Error", 
                                                            f"Error during verification: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set(f"Verification error: {str(e)}"))
        
        # Run verification in a separate thread to avoid blocking UI
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def run(self):
        """Run the log viewer window"""
        self.root.mainloop()

def open_log_viewer(config, logger):
    """Open the log viewer window"""
    viewer = LogViewer(config, logger)
    viewer.run()