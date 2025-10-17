import os
import time
import csv
import configparser
import queue
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import messagebox

def resource_path(relative_path):
    """Get the absolute path to a resource, works for development and PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # In development, use the script's directory
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    # Check for local config.ini in the executable's directory first
    local_path = os.path.join(os.path.dirname(sys.executable), relative_path)
    if os.path.exists(local_path):
        return local_path
    # Fall back to bundled config.ini
    return os.path.join(base_path, relative_path)

class FolderWatcherHandler(FileSystemEventHandler):
    def __init__(self, popup_queue, retry_count, retry_delay):
        self.popup_queue = popup_queue
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    def on_created(self, event):
        if event.is_directory:
            folder_path = event.src_path
            print(f"New folder detected: {folder_path}")
            
            # Search for CSV files with retries
            csv_file = None
            for attempt in range(self.retry_count + 1):  # Include initial attempt
                # Search for CSV files recursively
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith('.csv'):
                            csv_file = os.path.join(root, file)
                            break
                    if csv_file:
                        break
                
                if csv_file:
                    break  # Found CSV, exit retry loop
                elif attempt < self.retry_count:
                    print(f"No CSV file found in folder: {folder_path}, retrying ({attempt + 1}/{self.retry_count})...")
                    time.sleep(self.retry_delay)
            
            if csv_file:
                print(f"Found CSV file: {csv_file}")
                
                # Parse the CSV assuming key-value pairs (column 0: key, column 1: value)
                data = {}
                try:
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if len(row) >= 2:
                                key = row[0].strip()
                                value = row[1].strip()
                                data[key] = value
                    
                    # Extract relevant fields
                    total_str = data.get('Total test cases', '0')
                    passed_str = data.get('Passed', '0')
                    device_num = data.get('Provisioned Device Number', '')
                    
                    print(f"Total test cases: {total_str}")
                    print(f"Passed: {passed_str}")
                    
                    if device_num:
                        try:
                            total = int(total_str)
                            passed = int(passed_str)
                            
                            if total == passed:
                                status = 'PASS'
                                print(f"Status: PASS (Total {total} equals Passed {passed})")
                                # Queue pop-up for PASS
                                self.popup_queue.put(('PASS', "Test Passed", "green"))
                            else:
                                status = 'FAIL'
                                print(f"Status: FAIL (Total {total} does not equal Passed {passed})")
                                # Queue pop-up for FAIL
                                self.popup_queue.put(('FAIL', "Test FAILED", "red"))
                            
                            # Create new folder name
                            new_folder_name = f"{device_num}_{status}"
                            parent_dir = os.path.dirname(folder_path)
                            new_path = os.path.join(parent_dir, new_folder_name)
                            
                            # Ensure the new path doesn't already exist
                            if os.path.exists(new_path):
                                print(f"Target path already exists: {new_path}")
                                return
                            
                            # Rename the folder
                            os.rename(folder_path, new_path)
                            print(f"Renamed folder to: {new_path}")
                        except ValueError as ve:
                            print(f"Error converting test case counts to integers: {ve}")
                        except OSError as ose:
                            print(f"Error renaming folder: {ose}")
                    else:
                        print("Provisioned Device Number not found in CSV.")
                except Exception as e:
                    print(f"Error processing CSV {csv_file}: {e}")
            else:
                print(f"No CSV file found in folder after {self.retry_count} retries: {folder_path}")

def show_popup(root, popup_queue):
    try:
        # Check if there are any pop-up requests in the queue
        status, message, color = popup_queue.get_nowait()
        popup = tk.Toplevel(root)
        popup.title("Test Result")
        # Set larger window size
        window_width = 400
        window_height = 200
        # Get screen dimensions
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        # Calculate position to center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
        # Center the label vertically and horizontally
        label = tk.Label(popup, text=message, fg=color, font=("Arial", 18))
        label.pack(expand=True, pady=20)
        # Bind any keypress to close the pop-up
        popup.bind('<Key>', lambda event: popup.destroy())
        # Ensure the pop-up grabs focus for keypress
        popup.focus_set()
        popup.after(3000, popup.destroy)  # Auto-close after 3 seconds
    except queue.Empty:
        pass
    root.after(100, show_popup, root, popup_queue)  # Check again after 100ms

if __name__ == "__main__":
    # Load watch path from config.ini
    config_file = "config.ini"
    config_file_path = resource_path(config_file)
    print(f"Loading config file: {config_file_path}")
    try:
        config = configparser.ConfigParser()
        config.read(config_file_path)
        if 'Settings' in config and 'watch_path' in config['Settings']:
            watch_path = config['Settings']['watch_path']
            # Load retry settings with defaults
            retry_count = int(config['Settings'].get('retry_count', '5'))
            retry_delay = float(config['Settings'].get('retry_delay', '2'))
        else:
            print(f"Error: 'watch_path' not specified in [Settings] section of {config_file}")
            exit(1)
    except configparser.Error as e:
        print(f"Error: Invalid INI format in {config_file}: {e}")
        exit(1)
    except FileNotFoundError:
        print(f"Error: Config file {config_file} not found")
        exit(1)
    except ValueError as e:
        print(f"Error: Invalid retry_count or retry_delay in {config_file}: {e}")
        exit(1)
    
    if not os.path.exists(watch_path):
        print(f"Watch path does not exist: {watch_path}")
    else:
        # Initialize tkinter and queue
        root = tk.Tk()
        root.withdraw()  # Hide the main tkinter window
        popup_queue = queue.Queue()
        
        event_handler = FolderWatcherHandler(popup_queue, retry_count, retry_delay)
        observer = Observer()
        observer.schedule(event_handler, path=watch_path, recursive=False)
        observer.start()
        print(f"Watching directory: {watch_path}")
        
        try:
            # Start the pop-up checking loop
            root.after(100, show_popup, root, popup_queue)
            while True:
                root.update()  # Process tkinter events
                time.sleep(0.1)  # Reduce CPU usage
        except KeyboardInterrupt:
            observer.stop()
            root.destroy()  # Clean up tkinter
        observer.join()