import subprocess
import sys
import os
import shutil

def run_command(command):
    result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

# Define the directory structure
base_dir = "venv"
venv_dir = os.path.join(base_dir, "cn2")

# Remove the existing directory if it exists
if os.path.exists(venv_dir):
    shutil.rmtree(venv_dir)

# Create the base directory if it doesn't exist
os.makedirs(base_dir, exist_ok=True)

# 1. Create a virtual environment in the "venv/cn2" directory
run_command(f"{sys.executable} -m venv {venv_dir}")

# 2. Activate the virtual environment
activate_script = os.path.join(venv_dir, "Scripts", "activate") if os.name == "nt" else os.path.join(venv_dir, "bin", "activate")

# Note: Instead of using 'source' which is a shell built-in command, we use the full path to the Python executable within the venv
python_executable = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")

# 3. Upgrade pip
run_command(f"{python_executable} -m pip install --upgrade pip")

# 4. Install cadnano2
run_command(f"{python_executable} -m pip install cadnano2")

print("Setup complete. The virtual environment 'venv/cn2' is ready and cadnano2 is installed.")

if os.name != "nt": 

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
  
    print("Alias added. Please restart your terminal.")
