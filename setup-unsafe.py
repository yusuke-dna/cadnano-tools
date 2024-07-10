# For older Python version that does not support SSL.
import subprocess
import sys
import os
import shutil

def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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
    run_command(f'"{venv_python_executable}" -m pip install pywin32 --trusted-host pypi.org --trusted-host files.pythonhosted.org')

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

# Define constants
HOME_DIR = os.path.expanduser("~")
BASE_DIR = os.path.join(HOME_DIR, "venv")
VENV_DIR = os.path.join(BASE_DIR, "cn2")
PYTHON_EXECUTABLE = os.path.join(VENV_DIR, "Scripts", "python.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "python")
DESKTOP_PATH = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop") if os.name == "nt" else None  # Only used for Win system.

# Remove the existing directory if it exists
if os.path.exists(VENV_DIR):
    shutil.rmtree(VENV_DIR)

# Create the base directory if it doesn't exist
os.makedirs(BASE_DIR, exist_ok=True)

# 1. Create a virtual environment in the "venv/cn2" directory
print("Creating virtual environment...")
run_command(f'"{sys.executable}" -m venv "{VENV_DIR}"')

# 2. Upgrade pip and install setuptools
print("Upgrading pip and installing setuptools...")
run_command(f'"{PYTHON_EXECUTABLE}" -m pip install --upgrade pip setuptools --trusted-host pypi.org --trusted-host files.pythonhosted.org')

# 3. Install cadnano2
print("Installing cadnano2...")
run_command(f'"{PYTHON_EXECUTABLE}" -m pip install cadnano2 --trusted-host pypi.org --trusted-host files.pythonhosted.org')

if os.name == "nt":
    # 4. Install pywin32 within the virtual environment
    print("Installing pywin32...")
    install_pywin32(PYTHON_EXECUTABLE)

    # Windows-specific shortcut creation
    
    # Step 1: Create a batch file to activate the environment and run cadnano2
    ACTIVATE_BAT = os.path.join(VENV_DIR, "Scripts", "activate.bat")
    RUN_CADNANO_BAT = os.path.join(VENV_DIR, "Scripts", "run_cadnano2.bat")
    CADNANO2_EXE = os.path.join(VENV_DIR, "Scripts", "cadnano2.exe")
    
    with open(RUN_CADNANO_BAT, "w") as file:
        file.write(f'call "{ACTIVATE_BAT}"\n')
        file.write(f'call "{CADNANO2_EXE}"\n')
    
    # Step 2: Use the virtual environment's Python executable to create the shortcut
    escaped_run_cadnano_bat = RUN_CADNANO_BAT.replace("\\", "\\\\")
    escaped_shortcut_path = os.path.join(DESKTOP_PATH, "cadnano2.lnk").replace("\\", "\\\\")
    run_command(
        f'"{PYTHON_EXECUTABLE}" -c "import pythoncom; from win32com.shell import shell, shellcon; '
        f'shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink); '
        f'shortcut.SetPath(\\"{escaped_run_cadnano_bat}\\"); '
        f'shortcut.SetDescription(\\"Activate cn2 environment and run cadnano2\\"); '
        f'shortcut.SetWorkingDirectory(\\"{os.path.dirname(escaped_run_cadnano_bat)}\\"); '
        f'persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile); '
        f'persist_file.Save(\\"{escaped_shortcut_path}\\", 0)"'
    )

    print(f"Shortcut created at {os.path.join(DESKTOP_PATH, 'cadnano2.lnk')}")
else:
    # Non-Windows: Define the alias you want to add
    alias_command = "alias cadnano2='source ~/venv/cn2/bin/activate && cadnano2'"
    
    # Define the paths to common shell configuration files
    shell_config_paths = [
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
    for path in shell_config_paths:
        add_alias_to_file(path, alias_command)
    
    print("Alias added. Please restart your terminal to apply the changes.")
