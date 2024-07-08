import subprocess
import sys
import os
import shutil

def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    rc = process.poll()
    err_output = process.stderr.read().strip()
    if err_output:
        print(f"Error: {err_output}")
    return rc

def install_pywin32():
    run_command(f'"{sys.executable}" -m pip install pywin32')

def create_windows_shortcut(target, shortcut_path, description=""):
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
    except ImportError:
        install_pywin32()
        import pythoncom
        from win32com.shell import shell, shellcon

    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
    )
    shortcut.SetPath(target)
    shortcut.SetDescription(description)
    shortcut.SetWorkingDirectory(os.path.dirname(target))
    shortcut.SetArguments('/k')
    
    persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(shortcut_path, 0)

# Define the directory structure
base_dir = "venv"
venv_dir = os.path.join(base_dir, "cn2")

# Remove the existing directory if it exists
if os.path.exists(venv_dir):
    shutil.rmtree(venv_dir)

# Create the base directory if it doesn't exist
os.makedirs(base_dir, exist_ok=True)

# 1. Create a virtual environment in the "venv/cn2" directory
print("Creating virtual environment...")
run_command(f'"{sys.executable}" -m venv "{venv_dir}"')

# Note: Instead of using 'source' which is a shell built-in command, we use the full path to the Python executable within the venv
python_executable = os.path.join(venv_dir, "Scripts", "python.exe")

# 3. Upgrade pip
print("Upgrading pip...")
run_command(f'"{python_executable}" -m pip install --upgrade pip')

# 4. Install cadnano2
print("Installing cadnano2...")
run_command(f'"{python_executable}" -m pip install cadnano2')

print("Setup complete. The virtual environment 'venv/cn2' is ready and cadnano2 is installed.")

if os.name == "nt":
    # Install pywin32 if not already installed
    install_pywin32()
    
    # Windows-specific shortcut creation
    
    # Step 1: Create a batch file to activate the environment and run cadnano2
    activate_bat = os.path.join(venv_dir, "Scripts", "activate.bat")
    run_cadnano_bat = os.path.join(venv_dir, "Scripts", "run_cadnano2.bat")
    cadnano2_exe = os.path.join(venv_dir, "Scripts", "cadnano2.exe")
    
    with open(run_cadnano_bat, "w") as file:
        file.write(f'call "{activate_bat}"\n')
        file.write(f'call "{cadnano2_exe}"\n')
    
    # Step 2: Create a shortcut to run_cadnano2.bat on the Desktop
    desktop = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop")
    shortcut_path = os.path.join(desktop, "Run Cadnano2.lnk")
    create_windows_shortcut(run_cadnano_bat, shortcut_path, "Activate cn2 environment and run cadnano2")
    
    print(f"Shortcut created at {shortcut_path}")
else:
    print("This script is intended to be run on a Windows system.")
