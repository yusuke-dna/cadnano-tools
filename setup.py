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

def install_pywin32(venv_python_executable):
    run_command(f'"{venv_python_executable}" -m pip install pywin32')

def create_windows_shortcut(target, shortcut_path, description=""):
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
    except ImportError:
        raise ImportError("pywin32 not found. Please ensure it is installed in the virtual environment.")

    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
    )
    shortcut.SetPath(target)
    shortcut.SetDescription(description)
    shortcut.SetWorkingDirectory(os.path.dirname(target))
    
    persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(shortcut_path, 0)

# Get the home directory
home_dir = os.path.expanduser("~")

# Define the directory structure
base_dir = os.path.join(home_dir, "venv")
venv_dir = os.path.join(base_dir, "cn2")

# Remove the existing directory if it exists
if os.path.exists(venv_dir):
    shutil.rmtree(venv_dir)

# Create the base directory if it doesn't exist
os.makedirs(base_dir, exist_ok=True)

# 1. Create a virtual environment in the "venv/cn2" directory
print("Creating virtual environment...")
run_command(f'"{sys.executable}" -m venv "{venv_dir}"')

# Use the Python executable from within the virtual environment
python_executable = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")

# 2. Upgrade pip
print("Upgrading pip...")
run_command(f'"{python_executable}" -m pip install --upgrade pip')

# 3. Install cadnano2
print("Installing cadnano2...")
run_command(f'"{python_executable}" -m pip install cadnano2')

if os.name == "nt":
    # 4. Install pywin32 within the virtual environment
    print("Installing pywin32...")
    install_pywin32(python_executable)

    # Windows-specific shortcut creation
    
    # Step 1: Create a batch file to activate the environment and run cadnano2
    activate_bat = os.path.join(venv_dir, "Scripts", "activate.bat")
    run_cadnano_bat = os.path.join(venv_dir, "Scripts", "run_cadnano2.bat")
    cadnano2_exe = os.path.join(venv_dir, "Scripts", "cadnano2.exe")
    
    with open(run_cadnano_bat, "w") as file:
        file.write(f'call "{activate_bat}"\n')
        file.write(f'call "{cadnano2_exe}"\n')
    
    # Step 2: Use the virtual environment's Python executable to create the shortcut
    venv_python_executable = os.path.join(venv_dir, "Scripts", "python.exe")
    escaped_run_cadnano_bat = run_cadnano_bat.replace("\\", "\\\\")
    escaped_shortcut_path = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop", "cadnano2.lnk").replace("\\", "\\\\")
    run_command(
        f'"{venv_python_executable}" -c "import pythoncom; from win32com.shell import shell, shellcon; '
        f'shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink); '
        f'shortcut.SetPath(\\"{escaped_run_cadnano_bat}\\"); '
        f'shortcut.SetDescription(\\"Activate cn2 environment and run cadnano2\\"); '
        f'shortcut.SetWorkingDirectory(\\"{os.path.dirname(escaped_run_cadnano_bat)}\\"); '
        f'persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile); '
        f'persist_file.Save(\\"{escaped_shortcut_path}\\", 0)"'
    )

    print(f"Shortcut created at {os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop', 'Run Cadnano2.lnk')}")
else:
    # Non-Windows: Define the alias you want to add
    alias_command = "alias cadnano2='source ~/venv/cn2/bin/activate && cadnano2'"
    
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
    
    print("Alias added. Please restart your terminal to apply the changes.")
