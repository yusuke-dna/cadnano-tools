#!/usr/bin/env python3
"""Install cadnano2 into an isolated environment managed by uv.

This replaces the previous virtualenv + pip installer. uv ships its own TLS
stack and can supply the Python interpreter itself, so the installation no
longer depends on which `python3` happens to be first on PATH (pyenv, conda,
Homebrew and the system Python all interfere with that) and no longer needs
the certificate-verification workaround the old `-unsafe` flag provided.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE = "cadnano2"
COMMAND = "cadnano2"

# PyQt6 wheels are cp310-abi3, so anything from 3.10 works. 3.12 is pinned as a
# conservative, widely tested default rather than tracking the newest release.
DEFAULT_PYTHON = "3.12"

INSTALLER_URL_UNIX = "https://astral.sh/uv/install.sh"
INSTALLER_URL_WINDOWS = "https://astral.sh/uv/install.ps1"

MARKER_BEGIN = "# >>> cadnano-tools >>>"
MARKER_END = "# <<< cadnano-tools <<<"

LEGACY_VENV = Path.home() / "venv" / "cn2"

# Files the old installer could have written its alias into.
LEGACY_RC_FILES = (
    ".zprofile",
    ".zshrc",
    ".bash_profile",
    ".bashrc",
    ".profile",
    ".cshrc",
    ".tcshrc",
    Path(".config") / "fish" / "config.fish",
)

# Matches `alias cadnano2=...` (sh/bash/zsh/fish) and `alias cadnano2 ...` (csh).
LEGACY_ALIAS_RE = re.compile(r"^\s*alias\s+cadnano2\b\s*=?", re.IGNORECASE)

TLS_ERROR_HINTS = (
    "certificate",
    "self-signed",
    "self signed",
    "ssl",
    "tls",
    "unknownissuer",
    "invalid peer certificate",
)


def info(message):
    # Flushed so that stdout stays interleaved correctly with stderr and with
    # subprocess output when this script's output is piped to a file.
    print(message, flush=True)


def warn(message):
    sys.stdout.flush()
    print(f"warning: {message}", file=sys.stderr, flush=True)


def fail(message):
    sys.stdout.flush()
    print(f"error: {message}", file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd, check=True, capture=False, env=None, timeout=None):
    """Run a command without a shell, so paths containing spaces stay intact.

    subprocess.run() communicates on both pipes at once; the previous
    implementation read stdout to completion before touching stderr, which
    deadlocked whenever a child filled the stderr pipe buffer.
    """
    info("$ " + " ".join(str(part) for part in cmd))
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            text=True,
            capture_output=capture,
            env=env,
            timeout=timeout,
        )
    except FileNotFoundError:
        fail(f"command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        fail(f"command timed out after {timeout}s: {cmd[0]}")
    if capture and proc.stdout:
        print(proc.stdout, end="")
    if capture and proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        fail(f"command failed with exit code {proc.returncode}")
    return proc


def confirm(question, assume_yes):
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        warn("no interactive terminal available; re-run with --yes to proceed")
        return False
    try:
        answer = input(f"{question} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")


# --------------------------------------------------------------------------
# uv discovery and bootstrap
# --------------------------------------------------------------------------


def uv_candidates():
    """Places uv may sit when it is installed but not yet on PATH.

    The environment variables come first because the official installer obeys
    them: a bootstrap driven by UV_INSTALL_DIR or XDG_BIN_HOME lands outside
    ~/.local/bin, and looking only in the default would report the freshly
    installed uv as missing.
    """
    home = Path.home()
    name = "uv.exe" if os.name == "nt" else "uv"
    dirs = []

    for variable in ("UV_INSTALL_DIR", "XDG_BIN_HOME"):
        value = os.environ.get(variable)
        if value:
            dirs.append(Path(value))
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        dirs.append(Path(data_home).parent / "bin")
    cargo_home = os.environ.get("CARGO_HOME")
    if cargo_home:
        dirs.append(Path(cargo_home) / "bin")

    dirs.extend([home / ".local" / "bin", home / ".cargo" / "bin"])
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            dirs.append(Path(local_app_data) / "Microsoft" / "WinGet" / "Links")
        dirs.append(home / "scoop" / "shims")
    else:
        dirs.extend([Path("/opt/homebrew/bin"), Path("/usr/local/bin")])

    return [directory / name for directory in dirs]


def find_uv():
    found = shutil.which("uv")
    if found:
        return found
    for candidate in uv_candidates():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def bootstrap_uv():
    """Install uv using the official installer.

    This runs without asking. uv is not an optional extra here -- it is the
    package manager this script installs cadnano2 with -- so a prompt would
    only offer a choice between installing it and doing nothing. The steps are
    announced instead, so the user can see what was fetched and from where.
    """
    url = INSTALLER_URL_WINDOWS if os.name == "nt" else INSTALLER_URL_UNIX
    info("")
    info("=" * 72)
    info("uv was not found on this system, so it will be installed now.")
    info("")
    info("  what      uv, the package manager used to install cadnano2")
    info(f"  source    {url}  (official installer, Astral)")
    info("  where     ~/.local/bin")
    info("  rights    no administrator privileges required")
    info("")
    info("The installer also adds ~/.local/bin to your shell configuration.")
    info("To skip this step, install uv yourself and re-run:")
    if os.name == "nt":
        info(f'    powershell -ExecutionPolicy ByPass -c "irm {url} | iex"')
    else:
        info(f"    curl -LsSf {url} | sh")
    info("=" * 72)

    # Download to a file first rather than piping straight into a shell, so a
    # truncated download cannot be executed halfway.
    tmpdir = Path(tempfile.mkdtemp(prefix="cadnano-uv-"))
    try:
        if os.name == "nt":
            script = tmpdir / "install.ps1"
            run(
                ["powershell", "-NoProfile", "-Command", f"irm {url} -OutFile '{script}'"],
                timeout=120,
            )
        else:
            script = tmpdir / "install.sh"
            run(
                ["curl", "-fLsS", "--proto", "=https", "--tlsv1.2", "-o", str(script), url],
                timeout=120,
            )

        size = script.stat().st_size
        if size == 0:
            fail("the downloaded uv installer was empty")
        info(f"Downloaded installer ({size} bytes).")

        if os.name == "nt":
            run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                timeout=600,
            )
        else:
            run(["sh", str(script)], timeout=600)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    uv = find_uv()
    if not uv:
        searched = "\n".join(f"    {candidate}" for candidate in uv_candidates())
        fail(
            "the uv installer reported success, but uv could not be found.\n"
            "Looked in:\n" + searched + "\n"
            "Set UV_INSTALL_DIR to the directory it was installed into, or open\n"
            "a new terminal (which will pick up the updated PATH) and re-run."
        )
    info(f"uv installed at {uv}")
    return uv


# --------------------------------------------------------------------------
# Installing cadnano2
# --------------------------------------------------------------------------


def looks_like_tls_failure(proc):
    haystack = ((proc.stdout or "") + (proc.stderr or "")).lower()
    return any(hint in haystack for hint in TLS_ERROR_HINTS)


def uv_env(system_certs=False):
    """Environment for uv subprocesses.

    python-preference is deliberately not set here: uv rejects it alongside the
    --managed-python flag we pass. System certificates are selected through the
    environment because --system-certs is a global option that `uv tool install`
    does not accept in its own argument list.
    """
    env = dict(os.environ)
    env["UV_PYTHON_DOWNLOADS"] = "automatic"
    if system_certs:
        # Renamed from UV_NATIVE_TLS in uv 0.11. Older uv ignores unknown
        # variables, so setting only the current name degrades quietly.
        env["UV_SYSTEM_CERTS"] = "true"
    return env


def ensure_python(uv, python_version, system_certs):
    """Download the interpreter first, so its failures are distinguishable."""
    info(f"Ensuring a uv-managed Python {python_version} is available...")
    return run(
        [uv, "python", "install", "--managed-python", python_version],
        check=False,
        capture=True,
        env=uv_env(system_certs),
    )


def install_cadnano2(uv, python_version, system_certs, insecure, reinstall, upgrade):
    """Install cadnano2, escalating through TLS strategies only when needed."""
    if upgrade:
        base = [uv, "tool", "upgrade", PACKAGE]
    else:
        # A plain `uv tool install` is already idempotent: it is a no-op when the
        # tool is present and matches. --force rebuilds from scratch.
        base = [uv, "tool", "install"]
        if reinstall:
            base.append("--force")
        base += ["--managed-python", "--python", python_version, PACKAGE]

    if insecure:
        attempts = [(True, insecure_flags(), "with certificate verification relaxed")]
    elif system_certs:
        attempts = [(True, [], "using the system certificate store")]
    else:
        attempts = [(False, [], None), (True, [], "using the system certificate store")]

    last = None
    for index, (certs, extra, note) in enumerate(attempts):
        if index > 0:
            info("")
            warn("certificate verification failed; a TLS-inspecting proxy is likely.")
            info(f"Retrying {note}...")

        env = uv_env(certs)

        if not upgrade:
            python_proc = ensure_python(uv, python_version, certs)
            if python_proc.returncode != 0:
                last = python_proc
                if index + 1 < len(attempts) and looks_like_tls_failure(python_proc):
                    continue
                fail(
                    f"could not obtain a uv-managed Python {python_version}.\n"
                    + tls_guidance(python_proc)
                )

        last = run(base + extra, check=False, capture=True, env=env)
        if last.returncode == 0:
            if index > 0:
                info("")
                info("Succeeded. Pass --system-certs next time to skip the first attempt.")
            return
        if index + 1 < len(attempts) and not looks_like_tls_failure(last):
            break

    report_install_failure(last)


def insecure_flags():
    return [
        "--allow-insecure-host",
        "pypi.org",
        "--allow-insecure-host",
        "files.pythonhosted.org",
    ]


def tls_guidance(proc):
    if proc is None or not looks_like_tls_failure(proc):
        return "Check the output above for the underlying error."
    return (
        "\nThis is a certificate problem, which usually means a TLS-inspecting proxy\n"
        "on your network. Options, in order of preference:\n"
        "  1. Ask your IT department for the organisation's root CA and install it\n"
        "     into your operating system's certificate store, then re-run with\n"
        "     --system-certs.\n"
        "  2. Point uv at a CA bundle directly:\n"
        "       export SSL_CERT_FILE=/path/to/ca-bundle.pem\n"
        "  3. As a last resort, re-run with --allow-insecure-host. That disables\n"
        "     certificate verification for pypi.org and files.pythonhosted.org only,\n"
        "     rather than globally as the old -unsafe flag did."
    )


def report_install_failure(proc):
    fail(f"could not install {PACKAGE}.\n" + tls_guidance(proc))


def tool_bin_dir(uv):
    """Directory uv links tool executables into."""
    proc = subprocess.run(
        [uv, "tool", "dir", "--bin"], text=True, capture_output=True
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip())
    override = os.environ.get("UV_TOOL_BIN_DIR")
    if override:
        return Path(override)
    return Path.home() / ".local" / "bin"


# --------------------------------------------------------------------------
# Shell detection and PATH configuration
# --------------------------------------------------------------------------


def detect_login_shell():
    """Return the login shell's basename, e.g. 'zsh', or None if undeterminable."""
    shell = os.environ.get("SHELL")
    if not shell:
        try:
            import pwd

            shell = pwd.getpwuid(os.getuid()).pw_shell
        except Exception:
            return None
    if not shell:
        return None
    return Path(shell).name.lower()


def rc_file_for(shell):
    """Map a shell to the file that configures its interactive sessions."""
    home = Path.home()
    if shell == "zsh":
        zdotdir = os.environ.get("ZDOTDIR")
        return (Path(zdotdir) if zdotdir else home) / ".zshrc"
    if shell == "bash":
        # macOS terminals start login shells, which read .bash_profile and never
        # .bashrc. Linux terminals start non-login interactive shells, which do
        # the opposite.
        return home / (".bash_profile" if sys.platform == "darwin" else ".bashrc")
    if shell == "fish":
        return home / ".config" / "fish" / "config.fish"
    if shell in ("tcsh", "csh"):
        return home / (".tcshrc" if shell == "tcsh" else ".cshrc")
    return None


def home_relative(bin_dir):
    """Write $HOME rather than an expanded path, so the line stays portable."""
    home = str(Path.home())
    text = str(bin_dir)
    if text == home:
        return "$HOME"
    if text.startswith(home + os.sep):
        return "$HOME/" + text[len(home) + 1 :].replace(os.sep, "/")
    return text


def path_snippet(shell, bin_dir):
    location = home_relative(bin_dir)
    if shell == "fish":
        return f'fish_add_path "{location}"'
    if shell in ("csh", "tcsh"):
        return f'setenv PATH "{location}:$PATH"'
    # The guard makes the line self-idempotent, so sourcing the file twice
    # (as .bash_profile -> .bashrc chains do) cannot stack duplicate entries.
    return (
        f'case ":$PATH:" in\n'
        f'  *":{location}:"*) ;;\n'
        f'  *) export PATH="{location}:$PATH" ;;\n'
        f"esac"
    )


def path_variants(bin_dir):
    """Spellings of bin_dir that could already appear in a config file."""
    home = str(Path.home())
    text = str(bin_dir)
    variants = {text}
    if text.startswith(home):
        tail = text[len(home) :]
        variants.update({f"$HOME{tail}", f"${{HOME}}{tail}", f"~{tail}"})
    return variants


def mentions_bin_dir(text, bin_dir):
    """Line numbers that put bin_dir on PATH, ignoring commented-out lines."""
    variants = path_variants(bin_dir)
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # Case-insensitive: fish spells it `fish_add_path`, sh spells it `PATH`.
        if stripped.startswith("#") or "path" not in stripped.lower():
            continue
        if any(variant in stripped for variant in variants):
            hits.append(number)
    return hits


def already_on_path(bin_dir):
    """True if bin_dir is on the current PATH, comparing resolved paths."""
    try:
        target = bin_dir.resolve()
    except OSError:
        target = bin_dir
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).expanduser().resolve() == target:
                return True
        except OSError:
            continue
    return False


def windows_user_path():
    """Read the persistent per-user PATH from the registry. Read-only."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "Path")
        return os.path.expandvars(value)
    except (ImportError, FileNotFoundError, OSError):
        return None


def windows_path_contains(path_value, bin_dir):
    """Compare against a Windows PATH string.

    Windows semantics are spelled out rather than taken from os.path, so this
    stays correct (and testable) when the string is inspected from another
    platform: ';' separated, case-insensitive, '/' and '\\' interchangeable.
    """
    if not path_value:
        return False

    def normalise(text):
        return str(text).strip().strip('"').replace("/", "\\").rstrip("\\").lower()

    target = normalise(bin_dir)
    if not target:
        return False
    return any(
        normalise(entry) == target for entry in path_value.split(";") if entry.strip()
    )


def report_windows_path(bin_dir):
    """Explain whether cmd.exe will find cadnano2. Changes nothing.

    Windows keeps PATH in HKCU\\Environment rather than in a file the user
    edits, so a change there reaches every process the account starts. That is
    the user's call to make, not the installer's; this only reports the state
    and shows the commands.
    """
    if windows_path_contains(windows_user_path(), bin_dir):
        info("")
        info(f"{bin_dir} is on your user PATH.")
        info("Open a NEW Command Prompt to use `cadnano2` -- a window that was")
        info("already open keeps the PATH it started with.")
        return

    info("")
    info(f"{bin_dir} is not on your PATH, so `{COMMAND}` will not run from")
    info("cmd.exe or PowerShell. The desktop shortcut works either way.")
    info("")
    info("To enable the command line, run one of these yourself and then open")
    info("a new Command Prompt:")
    info("    uv tool update-shell")
    info(f'    setx PATH "%PATH%;{bin_dir}"')
    info("")
    info(f"Or start cadnano2 by full path:  {bin_dir / COMMAND}")


def configure_path(bin_dir, assume_yes):
    """Add bin_dir to PATH in the login shell's config file, idempotently."""
    shell = detect_login_shell()
    if not shell:
        manual_path_instructions(bin_dir, None)
        return

    rc = rc_file_for(shell)
    if rc is None:
        manual_path_instructions(bin_dir, shell)
        return

    if os.name != "nt" and os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        warn("running under sudo; refusing to write root-owned files into your home")
        manual_path_instructions(bin_dir, shell)
        return

    existing = rc.read_text(encoding="utf-8", errors="surrogateescape") if rc.exists() else ""
    if MARKER_BEGIN in existing:
        info(f"PATH entry already present in {rc}")
        return
    duplicates = mentions_bin_dir(existing, bin_dir)
    if duplicates:
        lines = ", ".join(f"line {number}" for number in duplicates)
        info(f"{rc} already puts {bin_dir} on PATH ({lines}); leaving it untouched")
        return

    info("")
    info(f"Detected login shell: {shell}")
    info(f"{bin_dir} is not on your PATH, so `{COMMAND}` would not be found.")
    info(f"The following lines would be appended to {rc}:")
    info("")
    block = (
        f"{MARKER_BEGIN}\n"
        "# Added by cadnano-tools setup.py. Deleting this whole block is safe.\n"
        f"{path_snippet(shell, bin_dir)}\n"
        f"{MARKER_END}"
    )
    for line in block.splitlines():
        info(f"    {line}")
    info("")
    if not confirm(f"Append these lines to {rc}?", assume_yes):
        manual_path_instructions(bin_dir, shell)
        return

    rc.parent.mkdir(parents=True, exist_ok=True)
    prefix = "" if (not existing or existing.endswith("\n")) else "\n"
    with rc.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}\n{block}\n")
    info(f"Updated {rc}. Open a new terminal for the change to take effect.")


def manual_path_instructions(bin_dir, shell):
    info("")
    warn(f"{bin_dir} is not on your PATH and was not configured automatically.")
    info("Add it by hand with the line appropriate for your shell:")
    info(f"    bash/zsh: export PATH=\"{bin_dir}:$PATH\"")
    info(f"    fish:     fish_add_path \"{bin_dir}\"")
    info(f"    csh/tcsh: setenv PATH \"{bin_dir}:$PATH\"")
    if shell:
        info(f"(detected shell: {shell})")
    info(f"Until then you can run {COMMAND} by its full path: {bin_dir / COMMAND}")


# --------------------------------------------------------------------------
# Reporting leftovers from the previous installer
# --------------------------------------------------------------------------


def find_legacy_aliases():
    """Locate — never modify — aliases written by earlier versions of this script."""
    home = Path.home()
    hits = []
    for name in LEGACY_RC_FILES:
        path = home / name
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="surrogateescape").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            if line.lstrip().startswith("#"):
                continue
            if LEGACY_ALIAS_RE.match(line):
                hits.append((path, number, line.strip()))
    return hits


def report_legacy_aliases():
    """A leftover alias shadows the new command, so this warning leads the report."""
    hits = find_legacy_aliases()
    if not hits:
        return 0

    info("")
    info("=" * 72)
    warn(f"ACTION REQUIRED: {len(hits)} old alias(es) are shadowing the new {COMMAND}.")
    info("=" * 72)
    for path, number, line in hits:
        info(f"    {path}:{number}")
        info(f"        {line}")
    info("")
    info("An alias always wins over a command found on PATH. Until you delete the")
    info(f"lines above, typing `{COMMAND}` will keep launching the old environment")
    info("and this migration will appear to have done nothing.")
    info("")
    info("Remove those lines in your editor, then open a new terminal.")
    info("This script does not edit your shell configuration files.")
    info("=" * 72)
    return len(hits)


def report_legacy_venv():
    if not LEGACY_VENV.exists():
        return
    info("")
    info(f"The previous installation is still present at {LEGACY_VENV}.")
    info("It is no longer used and can be removed once you have confirmed the new")
    info(f"installation works:  rm -rf {LEGACY_VENV}")


# --------------------------------------------------------------------------
# Windows desktop shortcut
# --------------------------------------------------------------------------


def windows_desktop_dir():
    """Ask Windows where Desktop actually is; OneDrive commonly redirects it."""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "[Environment]::GetFolderPath('Desktop')"],
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        candidate = Path(proc.stdout.strip())
        if candidate.is_dir():
            return candidate
    return Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"


def find_windows_launcher(bin_dir):
    """Prefer a windowed launcher so no console window accompanies the GUI."""
    for name in (f"{COMMAND}w.exe", f"{COMMAND}-gui.exe", f"{COMMAND}.exe"):
        candidate = bin_dir / name
        if candidate.exists():
            return candidate
    return None


def create_windows_shortcut(bin_dir):
    """Create a desktop shortcut via PowerShell, so pywin32 is not needed."""
    target = find_windows_launcher(bin_dir)
    if target is None:
        warn(f"no {COMMAND} executable found in {bin_dir}; skipping desktop shortcut")
        return

    desktop = windows_desktop_dir()
    if not desktop.is_dir():
        warn(f"{desktop} not found; skipping desktop shortcut")
        return

    shortcut = desktop / f"{COMMAND}.lnk"
    # cadnano2 is declared as a console script, so the plain .exe carries a
    # console window. WindowStyle 7 starts it minimised, out of the GUI's way.
    window_style = 1 if target.stem.endswith("w") else 7
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$sc = $ws.CreateShortcut('{shortcut}'); "
        f"$sc.TargetPath = '{target}'; "
        f"$sc.WorkingDirectory = '{Path.home()}'; "
        f"$sc.WindowStyle = {window_style}; "
        "$sc.Description = 'Launch cadnano2'; "
        "$sc.Save()"
    )
    proc = run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-c", script],
        check=False,
        capture=True,
    )
    if proc.returncode == 0:
        info(f"Shortcut created at {shortcut}")
    else:
        # The GUI itself installed fine, so this is not a fatal failure.
        warn(f"could not create the desktop shortcut; run {target} directly")


# --------------------------------------------------------------------------
# Uninstall
# --------------------------------------------------------------------------


def uninstall(uv):
    if not uv:
        fail("uv was not found, so there is nothing for this script to uninstall")
    run([uv, "tool", "uninstall", PACKAGE], check=False)
    if os.name == "nt":
        shortcut = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop" / f"{COMMAND}.lnk"
        if shortcut.exists():
            shortcut.unlink()
            info(f"Removed {shortcut}")
    info("")
    info("If this script added a PATH entry, it is delimited by these markers")
    info("in your shell configuration file and can be removed by hand:")
    info(f"    {MARKER_BEGIN}")
    info(f"    {MARKER_END}")
    report_legacy_aliases()
    report_legacy_venv()


# --------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Install cadnano2 into an isolated environment managed by uv."
    )
    parser.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        metavar="VERSION",
        help=f"Python version for the cadnano2 environment (default: {DEFAULT_PYTHON})",
    )
    parser.add_argument(
        "--system-certs",
        "--native-tls",
        action="store_true",
        dest="system_certs",
        help="use the operating system's certificate store (for TLS-inspecting proxies)",
    )
    parser.add_argument(
        "--allow-insecure-host",
        action="store_true",
        dest="insecure",
        help="last resort: skip certificate verification for pypi.org only",
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help=f"upgrade an existing {PACKAGE} installation to the latest release",
    )
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="rebuild the environment from scratch (use if it is broken)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what is installed and what needs attention, changing nothing",
    )
    parser.add_argument(
        "--no-shortcut",
        action="store_true",
        help="skip creating the Windows desktop shortcut",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="answer yes to prompts (currently only editing shell configuration)",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="remove cadnano2 and report anything left to clean up by hand",
    )
    parser.add_argument(
        "-unsafe",
        action="store_true",
        dest="legacy_unsafe",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def do_check():
    """Diagnostics only: report state without touching anything."""
    uv = find_uv()
    info(f"uv:            {uv or 'not installed'}")
    if uv:
        version = subprocess.run([uv, "--version"], text=True, capture_output=True)
        if version.returncode == 0:
            info(f"uv version:    {version.stdout.strip()}")
        bin_dir = tool_bin_dir(uv)
        on_path = "yes" if already_on_path(bin_dir) else "NO"
        info(f"tool bin dir:  {bin_dir}   [on PATH: {on_path}]")
        if os.name == "nt":
            persisted = windows_path_contains(windows_user_path(), bin_dir)
            info(f"user PATH:     {'registered' if persisted else 'NOT registered'}")
            if persisted and on_path == "NO":
                info("               (open a new Command Prompt to pick it up)")
        listing = subprocess.run([uv, "tool", "list"], text=True, capture_output=True)
        installed = [
            line for line in (listing.stdout or "").splitlines() if line.startswith(PACKAGE)
        ]
        info(f"{PACKAGE}:     {installed[0] if installed else 'not installed'}")

    shell = detect_login_shell()
    info(f"login shell:   {shell or 'undetermined'}")
    if shell:
        info(f"config file:   {rc_file_for(shell) or 'unknown for this shell'}")

    info(f"old venv:      {LEGACY_VENV if LEGACY_VENV.exists() else 'absent'}")
    hits = find_legacy_aliases()
    if hits:
        info(f"old aliases:   {len(hits)} found (must be removed)")
        for path, number, _ in hits:
            info(f"               {path}:{number}")
    else:
        info("old aliases:   none")

    resolved = shutil.which(COMMAND)
    info(f"`{COMMAND}` resolves to: {resolved or 'nothing on PATH'}")


def main():
    args = parse_args()

    if args.legacy_unsafe:
        warn(
            "-unsafe is deprecated. uv bundles its own TLS stack, so the certificate\n"
            "         problems it worked around should no longer occur. Falling back to\n"
            "         --system-certs; use --allow-insecure-host if that is not enough."
        )
        args.system_certs = True

    if args.check:
        do_check()
        return

    if args.uninstall:
        uninstall(find_uv())
        return

    uv = find_uv() or bootstrap_uv()
    info(f"Using uv at {uv}")

    install_cadnano2(
        uv, args.python, args.system_certs, args.insecure, args.reinstall, args.upgrade
    )

    bin_dir = tool_bin_dir(uv)
    info("")
    info(f"{PACKAGE} installed. Executable directory: {bin_dir}")

    if os.name == "nt":
        if not already_on_path(bin_dir):
            report_windows_path(bin_dir)
        if not args.no_shortcut:
            create_windows_shortcut(bin_dir)
    elif not already_on_path(bin_dir):
        configure_path(bin_dir, args.yes)

    report_legacy_aliases()
    report_legacy_venv()

    info("")
    info("Done. Open a new terminal, then start cadnano2 by running:")
    info(f"    {COMMAND}")
    if os.name == "nt":
        info("A new Command Prompt is required: open windows keep the old PATH.")
        info("You can also double-click the cadnano2 shortcut on your desktop.")


if __name__ == "__main__":
    main()
