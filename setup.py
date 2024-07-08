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
    run_command(f"{sys.executable} -m pip install pywin32")

def create_windows_shortcut(target, shortcut_path, description=""):
    import pythoncom
    from win32com.shell import shell, shellcon

    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
    )
    shortcut.SetPath(target)
    shortcut.SetDescription(description)
    shortcut.SetWorkingDirectory(os.path.dirname(target))
    
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
run_command(f"{sys.executable} -m venv {venv_dir}")

# 2. Activate the virtual environment
activate_script = os.path.join(venv_dir, "Scripts", "activate") if os.name == "nt" else os.path.join(venv_dir, "bin", "activate")

# Note: Instead of using 'source' which is a shell built-in command, we use the full path to the Python executable within the venv
python_executable = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")

# 3. Upgrade pip
print("Upgrading pip...")
run_command(f"{python_executable} -m pip install --upgrade pip")

# 4. Install cadnano2
print("Installing cadnano2...")
run_command(f"{python_executable} -m pip install cadnano2")

print("Setup complete. The virtual environment 'venv/cn2' is ready and cadnano2 is installed.")

if os.name == "nt":
    # Install pywin32 if not already installed
    install_pywin32()
    
    # Windows-specific shortcut creation
    
    # Step 1: Duplicate activate.bat and rename the copy to cadnano2.bat
    activate_bat = os.path.join(venv_dir, "Scripts", "activate.bat")
    cadnano2_bat = os.path.join(venv_dir, "Scripts", "cadnano2.bat")
    cadnano2_exe = os.path.join(venv_dir, "Scripts", "cadnano2.exe")
    shutil.copyfile(activate_bat, cadnano2_bat)
    
    # Step 2: Add cadnano2 to the last line of cadnano2.bat
    with open(cadnano2_bat, "a") as file:
        file.write(f"\ncall {cadnano2_exe}\n")
    
    # Step 3: Create a shortcut to cadnano2.bat on the Desktop
    desktop = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop")
    shortcut_path = os.path.join(desktop, "cadnano2.lnk")
    create_windows_shortcut(cadnano2_bat, shortcut_path, "Activate cn2 environment and run cadnano2")
    
    print(f"Shortcut created at {shortcut_path}")
else:
    # Define the alias you want to add
    alias_command = "alias activate_cn2='source ~/venv/cn2/bin/activate && cadnano2'"
    
    # Define the paths to common zsh configuration files
    zshrc_paths = [
        os.path.expanduser("~/.zshrc"),
        os.path.expanduser("~/.zprofile"),
        os.path.expanduser("~/.profile"),
        os.path.expanduser("~/.bash_profile")
    ]
    
    # Function to add alias to the specified file if it exists
    def add_alias_to_file(file_path, alias_command):
        if os.path.exists(file_path):
            with open(file_path, "a") as file:
                file.write(f"\n{alias_command}\n")
            print(f"Alias added to {file_path}")
    
    # Add the alias to all relevant configuration files
    for path in zshrc_paths:
        add_alias_to_file(path, alias_command)
    
    print("Alias added. Please restart your terminal or run 'source ~/.zshrc' to apply the changes.")
