import os
import csv
import glob
import platform

def check_csv_summary(csv_path, expected_device_number):
    """
    Reads a CSV file assuming rows are in key-value format (e.g., 'Total test cases', '26').
    Parses first column as key, second as value (tries to convert to int for numeric fields).
    Checks 'Total test cases', 'Passed', and 'Provisioned Device Number'.
    Returns (total_test_cases, passed, device_number) or (None, None, None) if error.
    """
    data = {}
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, 1):
                if len(row) >= 2 and row[0].strip():
                    key = row[0].strip()
                    value = row[1].strip()
                    if key in ['Total test cases', 'Passed']:
                        try:
                            data[key] = int(value)
                        except ValueError:
                            continue  # Skip non-integer values for numeric fields
                    else:
                        data[key] = value  # Keep as string for Provisioned Device Number
        return (
            data.get('Total test cases'),
            data.get('Passed'),
            data.get('Provisioned Device Number')
        )
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return None, None, None

# Main script
# Set large console size and buffer for Windows
if platform.system() == "Windows":
    # Set console to a large size (150 columns x 50 lines) and buffer for scrolling
    os.system("mode con: cols=150 lines=50")
    os.system("powershell -command \"$Host.UI.RawUI.BufferSize = New-Object Management.Automation.Host.Size(150,1000)\"")

parent_dir = input("Enter the path to the directory containing the Aikri folders: ").strip()

# Verify parent directory exists
if not os.path.isdir(parent_dir):
    print(f"Invalid directory: {parent_dir}")
    input("Press Enter to exit...")
    exit(1)

# Find folders matching pattern "Aikri-85X-50LS-16-*" in the specified path
pattern = os.path.join(parent_dir, "Aikri-85X-50LS-16-*")
folders = [f for f in glob.glob(pattern) if os.path.isdir(f)]

if not folders:
    print(f"No matching folders found in {parent_dir} (looking for Aikri-85X-50LS-16-*).")
    input("Press Enter to exit...")
    exit(1)

# Print header
print(f"{'Folders':<35} | {'Total Test':<10} | {'Provision Device Number'}")
print("-" * 70)

for folder in sorted(folders):
    folder_name = os.path.basename(folder)
    # Look for CSV with name <folder_name>_Test_Result.csv
    csv_path = os.path.join(folder, f"{folder_name}_Test_Result.csv")
    
    if not os.path.isfile(csv_path):
        print(f"{folder_name:<35} | {'NO CSV FILE':<10} | {'NO CSV FILE'}")
        continue
    
    total, passed, device_number = check_csv_summary(csv_path, folder_name)
    
    # Check conditions
    tests_pass = total == 26 and passed == 26
    device_match = device_number == folder_name
    
    # Format Total Test column
    total_test = 'PASS' if tests_pass else 'FAIL'
    
    # Format Provision Device Number column
    device_status = 'Pass' if device_match else 'FAIL'
    
    print(f"{folder_name:<35} | {total_test:<10} | {device_status}")

# Keep console open
input("\nPress Enter to exit...")