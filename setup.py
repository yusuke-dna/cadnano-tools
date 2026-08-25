#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
# The block above is PEP 723 inline metadata. It lets `uv run --script setup.py`
# supply an interpreter itself, so install.sh and install.bat can bootstrap the
# whole installation without a system Python. python3 setup.py still works: to
# Python the block is an ordinary comment.
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

# Child output is decoded as UTF-8 below, so re-printing it must never crash
# on a character the console encoding cannot represent -- on Windows a
# redirected stdout encodes with the ANSI code page and errors='strict', and
# uv's box-drawing characters (or U+FFFD from a lossy decode) would raise
# UnicodeEncodeError right where an error message was about to be shown.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

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
        # uv always writes UTF-8, while text=True alone would decode with the
        # locale encoding -- cp932 on Japanese Windows -- and crash on any
        # non-ASCII path in the output, such as a Japanese user name.
        proc = subprocess.run(
            [str(part) for part in cmd],
            text=True,
            encoding="utf-8",
            errors="replace",
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


def japanese_ui():
    """True when the user's interface language is Japanese.

    Only the decision-point dialogs introduced with the shortcut/conflict
    handling are translated; routine progress output stays English so logs
    remain greppable and support requests stay readable.
    """
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            return value.lower().startswith("ja")
    if os.name == "nt":
        try:
            import ctypes

            return (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x11
        except Exception:
            return False
    return False


JAPANESE_UI = japanese_ui()


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


_UV_VERSION_CACHE = {}

# uv 0.11 renamed UV_NATIVE_TLS to UV_SYSTEM_CERTS.
SYSTEM_CERTS_RENAMED_IN = (0, 11, 0)


def uv_version(uv):
    """(major, minor, patch) for this uv, or None if it cannot be read."""
    key = str(uv)
    if key not in _UV_VERSION_CACHE:
        parsed = None
        try:
            proc = subprocess.run(
                [key, "--version"],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=30,
            )
            if proc.returncode == 0:
                match = re.search(r"(\d+)\.(\d+)\.(\d+)", proc.stdout or "")
                if match:
                    parsed = tuple(int(part) for part in match.groups())
        except (OSError, subprocess.SubprocessError):
            parsed = None
        _UV_VERSION_CACHE[key] = parsed
    return _UV_VERSION_CACHE[key]


def system_certs_variable(uv):
    """The environment variable this uv understands for the system trust store.

    Picked by version rather than setting both names: uv ignores the name it
    does not know without complaining, so the wrong one fails silently, while
    setting both makes current uv warn about the deprecated one on every call.
    """
    version = uv_version(uv)
    if version is not None and version < SYSTEM_CERTS_RENAMED_IN:
        return "UV_NATIVE_TLS"
    return "UV_SYSTEM_CERTS"


def uv_env(uv, system_certs=False):
    """Environment for uv subprocesses.

    python-preference is deliberately not set here: uv rejects it alongside the
    --managed-python flag we pass. System certificates are selected through the
    environment because --system-certs is a global option that `uv tool install`
    does not accept in its own argument list.
    """
    env = dict(os.environ)
    env["UV_PYTHON_DOWNLOADS"] = "automatic"
    if system_certs:
        env[system_certs_variable(uv)] = "true"
    return env


def ensure_python(uv, python_version, system_certs):
    """Download the interpreter first, so its failures are distinguishable."""
    info(f"Ensuring a uv-managed Python {python_version} is available...")
    return run(
        [uv, "python", "install", "--managed-python", python_version],
        check=False,
        capture=True,
        env=uv_env(uv, system_certs),
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

        env = uv_env(uv, certs)

        if not upgrade:
            python_proc = ensure_python(uv, python_version, certs)
            if python_proc.returncode != 0:
                last = python_proc
                if index + 1 < len(attempts) and looks_like_tls_failure(python_proc):
                    continue
                outdated = outdated_uv_guidance(python_proc)
                if outdated:
                    fail(f"could not obtain a uv-managed Python {python_version}: {outdated}")
                fail(
                    f"could not obtain a uv-managed Python {python_version}.\n"
                    + python_download_guidance(python_proc)
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


def outdated_uv_guidance(proc):
    """A clap error about --managed-python means this uv predates the flag."""
    output = ((proc.stdout or "") + (proc.stderr or "")) if proc else ""
    if "unexpected argument" in output and "--managed-python" in output:
        if JAPANESE_UI:
            return (
                "このシステムの uv は古く、--managed-python を解釈できません。\n"
                "`uv self update`(または uv を入れたパッケージマネージャー)で\n"
                "更新してから、このスクリプトを再実行してください。"
            )
        return (
            "the uv found on this system is too old to understand\n"
            "--managed-python. Upgrade it with `uv self update` (or with the\n"
            "package manager that installed it) and run this script again."
        )
    return None


def python_download_guidance(proc):
    """Guidance for a failing `uv python install`.

    The interpreter archives come from GitHub, not PyPI, so the pypi.org-only
    --allow-insecure-host escape hatch does not apply here and must not be
    recommended.
    """
    if proc is None or not looks_like_tls_failure(proc):
        return "Check the output above for the underlying error."
    # By the time this shows, the system certificate store has already been
    # tried (the install flow retries with it automatically), so recommending
    # --system-certs here would just repeat what failed. The steps are ordered
    # by what a user can actually do without help.
    if JAPANESE_UI:
        return (
            "\nPython 本体を安全にダウンロードできませんでした。このネットワークが\n"
            "通信内容を検査する構成(大学や企業でよくある設定)の場合に、この\n"
            "症状になります。対処のおすすめ順:\n"
            "  1. 別のネットワークで再実行する(自宅の Wi-Fi やスマートフォンの\n"
            "     テザリングなど)。ダウンロードが必要なのはインストール時だけで、\n"
            "     その後は元のネットワークでも問題なく使えます。\n"
            "  2. 解決しない場合は、所属機関の IT 部門に「この端末に組織のルート\n"
            "     証明書が配布されているか」を確認してもらい、再実行してください。\n"
            "  3. 技術者向け: CA バンドルを直接指定して再実行できます:\n"
            "       export SSL_CERT_FILE=/path/to/ca-bundle.pem"
        )
    return (
        "\nThe Python interpreter itself could not be downloaded securely. This\n"
        "usually means the network inspects TLS traffic, which is common at\n"
        "universities and companies. Options, in order of preference:\n"
        "  1. Re-run on a different network (home Wi-Fi or a phone hotspot).\n"
        "     Only the installation needs the download; afterwards cadnano2\n"
        "     works fine on this network too.\n"
        "  2. If that is not possible, ask your IT department whether the\n"
        "     organisation's root certificate is deployed to this machine,\n"
        "     then re-run this installer.\n"
        "  3. For technicians: point uv at a CA bundle directly:\n"
        "       export SSL_CERT_FILE=/path/to/ca-bundle.pem"
    )


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
    outdated = outdated_uv_guidance(proc)
    if outdated:
        fail(f"could not install {PACKAGE}: {outdated}")
    fail(f"could not install {PACKAGE}.\n" + tls_guidance(proc))


def tool_bin_dir(uv):
    """Directory uv links tool executables into."""
    proc = subprocess.run(
        [uv, "tool", "dir", "--bin"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
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
    # The match must end at a path boundary, so `$HOME/.local/bin` is not
    # satisfied by `$HOME/.local/binaries` or `$HOME/.local/bin/tools`.
    patterns = [
        re.compile(re.escape(variant) + r"(?![\w/-])")
        for variant in path_variants(bin_dir)
    ]
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # Case-insensitive: fish spells it `fish_add_path`, sh spells it `PATH`.
        if stripped.startswith("#") or "path" not in stripped.lower():
            continue
        if any(pattern.search(stripped) for pattern in patterns):
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
        if JAPANESE_UI:
            info("次のディレクトリはユーザー PATH に登録されています:")
            info(f"    {bin_dir}")
            info("新しいコマンドプロンプトを開くと `cadnano2` が使えます。")
        else:
            info("This directory is on your user PATH:")
            info(f"    {bin_dir}")
            info("Open a NEW Command Prompt to use `cadnano2`.")
        return

    info("")
    if JAPANESE_UI:
        info("次のディレクトリが PATH にないため、cmd.exe や PowerShell から")
        info(f"`{COMMAND}` は起動できません(デスクトップのショートカットは使えます):")
        info(f"    {bin_dir}")
        info("")
        info("コマンドラインを有効にするには、次を実行してから新しいコマンド")
        info("プロンプトを開いてください:")
        info("    uv tool update-shell")
        info("")
        info("手動で設定する場合: スタートメニューで「環境変数」を検索し、")
        info('ユーザーの "Path" に次を追加してください:')
        info(f"    {bin_dir}")
        info("")
        info("フルパスでの起動も可能です:")
        info(f"    {bin_dir / COMMAND}")
        return
    info(f"This directory is not on your PATH, so `{COMMAND}` will not run")
    info("from cmd.exe or PowerShell (the desktop shortcut works either way):")
    info(f"    {bin_dir}")
    info("")
    info("To enable the command line, run this yourself and then open a new")
    info("Command Prompt:")
    info("    uv tool update-shell")
    info("")
    # setx is deliberately not suggested here: it truncates the stored PATH at
    # 1024 characters and merges the machine PATH into the user PATH.
    info("Or add the directory by hand: search the Start menu for")
    info('"environment variables", edit the user "Path" entry and add:')
    info(f"    {bin_dir}")
    info("")
    info("Or start cadnano2 by full path:")
    info(f"    {bin_dir / COMMAND}")


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
    info(f"This directory is not on your PATH, so `{COMMAND}` would not be found:")
    info(f"    {bin_dir}")
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
    info(f"Updated {rc}.")
    info("Open a new terminal for the change to take effect.")


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


def powershell_utf8(body):
    """Wrap a PowerShell command so its output is written as UTF-8.

    Pinning the console encoding lets a path containing a Japanese (or any
    non-ASCII) user name survive the pipe regardless of the system code page.
    The previous encoding is restored afterwards, because the child shares
    the parent console and the change would otherwise outlive this script.
    """
    return (
        "$__oe=[Console]::OutputEncoding; "
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "try { " + body + " } finally { [Console]::OutputEncoding=$__oe }"
    )


def windows_desktop_dir():
    """Ask Windows where Desktop actually is; OneDrive commonly redirects it."""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         powershell_utf8("[Environment]::GetFolderPath('Desktop')")],
        text=True,
        encoding="utf-8",
        errors="replace",
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
    """Create or refresh a desktop shortcut via PowerShell, without pywin32.

    Targets decide, not names: a shortcut already pointing at this
    installation is refreshed under whatever name the user gave it, while a
    cadnano2.lnk they made for some other installation is never overwritten
    -- the new shortcut is created as "cadnano2 (new)" beside it instead.
    """
    target = find_windows_launcher(bin_dir)
    if target is None:
        warn(f"no {COMMAND} executable found in {bin_dir}; skipping desktop shortcut")
        return

    desktop = windows_desktop_dir()
    if not desktop.is_dir():
        warn(f"{desktop} not found; skipping desktop shortcut")
        return

    existing = desktop_shortcuts(desktop)
    ours = [lnk for lnk, lnk_target in existing
            if shortcut_points_at_install(lnk_target, bin_dir)]
    renamed = False
    if ours:
        shortcut = ours[0]  # keep the name the user knows, even if they renamed it
    else:
        # Keep appending " (new)" until a free name turns up; the taken set is
        # finite, so this always terminates, and the announcement below shows
        # whichever name was actually used.
        taken = {lnk.name.lower() for lnk, _ in existing}
        stem = COMMAND
        shortcut = desktop / f"{stem}.lnk"
        while shortcut.name.lower() in taken:
            stem += " (new)"
            shortcut = desktop / f"{stem}.lnk"
            renamed = True
    # cadnano2 is declared as a console script, so the plain .exe carries a
    # console window. WindowStyle 7 starts it minimised, out of the GUI's way.
    window_style = 1 if target.stem.endswith("w") else 7
    # All paths travel through environment variables, never interpolated into
    # the command: the shortcut may carry a user-chosen name (they can rename
    # it), and an apostrophe in any of these would break single quoting.
    env = dict(
        os.environ,
        CADNANO_LNK=str(shortcut),
        CADNANO_TARGET=str(target),
        CADNANO_WORKDIR=str(Path.home()),
    )
    script = powershell_utf8(
        "$ws = New-Object -ComObject WScript.Shell; "
        "$sc = $ws.CreateShortcut($env:CADNANO_LNK); "
        "$sc.TargetPath = $env:CADNANO_TARGET; "
        "$sc.WorkingDirectory = $env:CADNANO_WORKDIR; "
        f"$sc.WindowStyle = {window_style}; "
        f"$sc.Description = '{'cadnano2 を起動' if JAPANESE_UI else 'Launch cadnano2'}'; "
        "$sc.Save()"
    )
    # -Command is not subject to the execution policy (only script files are),
    # so "-ExecutionPolicy Bypass" is not needed -- and the Bypass keyword is
    # exactly what antivirus heuristics watch for, so it is deliberately absent.
    proc = run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        capture=True,
        env=env,
    )
    if proc.returncode == 0:
        if renamed:
            if JAPANESE_UI:
                info(f"既存の {COMMAND} ショートカットは別のインストール先を指しているため")
                info(f'そのまま残し、こちらは "{shortcut.stem}" として作成しました。')
            else:
                info(f"An existing {COMMAND} shortcut points at another installation and")
                info(f'was left untouched; this one was installed as "{shortcut.stem}".')
        info(f"Shortcut created at {shortcut}")
    else:
        # The GUI itself installed fine, so this is not a fatal failure.
        warn(f"could not create the desktop shortcut; run {target} directly")


def shortcut_points_at_install(target, bin_dir):
    """True if a .lnk target is one of this installation's own launchers.

    Both the directory and the executable name are checked: a shortcut the
    user pointed at some other program that merely lives in the same bin
    directory is not ours to replace or delete.
    """
    if target is None:
        return False
    launchers = {f"{COMMAND}w.exe", f"{COMMAND}-gui.exe", f"{COMMAND}.exe"}
    return (
        os.path.normcase(os.path.normpath(str(target.parent)))
        == os.path.normcase(os.path.normpath(str(bin_dir)))
        and target.name.lower() in launchers
    )


def desktop_shortcuts(desktop):
    """[(path, target)] for every .lnk on the desktop, in one PowerShell call.

    Shortcut names are user-editable, so anything that needs to know which
    shortcut belongs to this installation must go by target, not by name.
    The desktop path travels through an environment variable rather than
    being interpolated into the command, so quoting cannot break on
    apostrophes or non-ASCII characters; '|' separates the fields because
    it cannot occur in a Windows path.
    """
    env = dict(os.environ, CADNANO_DESKTOP=str(desktop))
    body = (
        "$ws = New-Object -ComObject WScript.Shell; "
        "Get-ChildItem -LiteralPath $env:CADNANO_DESKTOP -Filter *.lnk | "
        "ForEach-Object { $_.FullName + '|' + $ws.CreateShortcut($_.FullName).TargetPath }"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", powershell_utf8(body)],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    pairs = []
    for line in (proc.stdout or "").splitlines():
        if "|" not in line:
            continue
        path_text, target_text = line.split("|", 1)
        if path_text.strip():
            target = Path(target_text.strip()) if target_text.strip() else None
            pairs.append((Path(path_text.strip()), target))
    return pairs


# --------------------------------------------------------------------------
# Conflict detection: other cadnano2 installations and conda
# --------------------------------------------------------------------------


def other_installations(bin_dir):
    """Every cadnano2 on PATH that is NOT the one in bin_dir, in PATH order.

    Nothing found here is ever removed: a cadnano2 the user installed
    themselves (pip, conda, an old venv) is not this script's to touch.
    Comparison and deduplication work on fully resolved paths, so the same
    file reached through a symlinked directory or a `..` spelling is neither
    double-reported nor mistaken for a second installation.
    """
    bin_dir = Path(bin_dir)
    try:
        expected = bin_dir.resolve()
    except OSError:
        expected = bin_dir

    # uv links bin_dir/cadnano2 into the tool environment, so anything that
    # resolves to the same final file is this installation too, however many
    # symlinks it was reached through.
    our_target = None
    ours = shutil.which(COMMAND, path=str(bin_dir))
    if ours:
        try:
            our_target = Path(ours).resolve()
        except OSError:
            our_target = Path(ours)

    others = []
    seen = set()
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry.strip():
            continue
        found = shutil.which(COMMAND, path=entry)
        if not found:
            continue
        candidate = Path(found)
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        try:
            parent_resolved = candidate.parent.resolve()
        except OSError:
            parent_resolved = candidate.parent
        if parent_resolved == expected or resolved == our_target:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        others.append(candidate)
    return others


def report_command_conflicts(bin_dir):
    """Warn when a different cadnano2 on PATH may shadow this installation."""
    others = other_installations(bin_dir)
    if not others:
        return
    resolved = shutil.which(COMMAND)
    info("")
    if JAPANESE_UI:
        warn(f"このインストールとは別の {COMMAND} が見つかりました:")
        for other in others:
            info(f"    {other}")
        if resolved:
            info(f"この端末で `{COMMAND}` と入力した場合に起動するのは:")
            info(f"    {resolved}")
        info("PATH で先に現れる方が優先されます。このスクリプトは自分が入れて")
        info("いないものを削除しません。不要であれば、それを入れたツール")
        info("(pip や conda、または仮想環境ごと削除)で取り除いてください。")
    else:
        warn(f"another {COMMAND} is installed outside this installation:")
        for other in others:
            info(f"    {other}")
        if resolved:
            info(f"In this terminal, `{COMMAND}` currently starts:")
            info(f"    {resolved}")
        info("Whichever comes first on PATH wins. This script never removes what it")
        info("did not install; if the other copy is unwanted, remove it with the")
        info("tool that installed it (pip, conda, or by deleting its environment).")


# --------------------------------------------------------------------------
# Local fix for a known upstream crash
# --------------------------------------------------------------------------


def patch_documentwindow(uv):
    """Guard a known cadnano2 crash: a window event before __init__ finishes.

    Upstream cadnano2's DocumentWindow.moveEvent/resizeEvent read
    self.settings, which __init__ assigns only after setupUi(); if the OS
    repositions the window during construction -- typical when the saved
    window position points at an external display -- the handler raises and
    PyQt6 aborts the whole process. Upgrading or reinstalling restores the
    unpatched file, so the guard is re-applied after every install.
    """
    try:
        proc = subprocess.run(
            [uv, "tool", "dir"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except OSError:
        return
    if proc.returncode != 0 or not proc.stdout.strip():
        return
    tools = Path(proc.stdout.strip())
    targets = list(
        tools.glob(f"{PACKAGE}/[Ll]ib/**/site-packages/cadnano2/views/documentwindow.py")
    )
    if not targets:
        return

    guard = "if not hasattr(self, 'settings'):"
    pattern = re.compile(
        r"(    def (?:move|resize)Event\(self, event\):\n"
        r'(?:        """[^\n]*"""\n)?)'
        r"(        self\.settings\.beginGroup)"
    )
    replacement = (
        "\\1        if not hasattr(self, 'settings'):\n"
        "            return\n"
        "\\2"
    )

    for target in targets:
        try:
            source = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            warn(f"could not read {target} to apply the known-crash guard: {exc}")
            continue
        if guard in source:
            continue  # already patched; a re-run should stay quiet
        patched, count = pattern.subn(replacement, source)
        if count == 0:
            warn(
                "cadnano2's window code no longer matches the known-crash guard;\n"
                "         skipping the local fix (upstream may have fixed it)."
            )
            continue
        try:
            compile(patched, str(target), "exec")
            target.write_text(patched, encoding="utf-8")
        except (OSError, SyntaxError) as exc:
            warn(f"could not apply the known-crash guard to {target}: {exc}")
            continue
        # Routine maintenance the user need not act on: silent on Windows
        # (double-clicked install.bat), a brief English note on install.sh.
        if os.name != "nt":
            info("Applied a local guard for a known cadnano2 crash (window moved")
            info("before initialisation finished, e.g. on an external display).")


LAUNCH_GUARD_MARKER = "# >>> cadnano-tools launch guard >>>"
LAUNCH_GUARD = (
    "# >>> cadnano-tools launch guard >>>\n"
    "# Added by cadnano-tools setup.py. conda activation and similar tools leak\n"
    "# QT_PLUGIN_PATH and PYTHONPATH into this otherwise isolated environment,\n"
    "# which can point Qt at foreign plugins and stop the window from opening.\n"
    "# Both are neutralised here, for cadnano2's own process only, before Qt\n"
    "# loads. Deleting this whole block is safe.\n"
    "def _cadnano_tools_launch_guard():\n"
    "    import os, sys\n"
    "    for name in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):\n"
    "        os.environ.pop(name, None)\n"
    "    pythonpath = os.environ.get('PYTHONPATH')\n"
    "    if pythonpath:\n"
    "        bad = {os.path.abspath(p) for p in pythonpath.split(os.pathsep) if p}\n"
    "        sys.path[:] = [p for p in sys.path if os.path.abspath(p) not in bad]\n"
    "\n"
    "\n"
    "_cadnano_tools_launch_guard()\n"
    "del _cadnano_tools_launch_guard\n"
    "# <<< cadnano-tools launch guard <<<\n"
)


def patch_launch_guard(uv):
    """Neutralise environment leaks that would break launching the GUI.

    uv's isolation covers packages, not the process environment: Python
    honours PYTHONPATH inside any environment, and Qt honours the plugin-path
    variables conda exports. Rather than warning the user about variables
    they did not set and may not understand, the installed package itself
    strips them at import time. Re-applied after every install, like the
    crash guard above.
    """
    try:
        proc = subprocess.run(
            [uv, "tool", "dir"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except OSError:
        return
    if proc.returncode != 0 or not proc.stdout.strip():
        return
    tools = Path(proc.stdout.strip())
    targets = list(
        tools.glob(f"{PACKAGE}/[Ll]ib/**/site-packages/cadnano2/__init__.py")
    )
    for target in targets:
        try:
            source = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            warn(f"could not read {target} to apply the launch guard: {exc}")
            continue
        if LAUNCH_GUARD_MARKER in source:
            continue  # already guarded; a re-run should stay quiet
        patched = LAUNCH_GUARD + source
        try:
            compile(patched, str(target), "exec")
            target.write_text(patched, encoding="utf-8")
        except (OSError, SyntaxError) as exc:
            warn(f"could not apply the launch guard to {target}: {exc}")


# --------------------------------------------------------------------------
# Uninstall
# --------------------------------------------------------------------------


def uninstall(uv):
    if not uv:
        fail("uv was not found, so there is nothing for this script to uninstall")
    bin_dir = tool_bin_dir(uv)
    run([uv, "tool", "uninstall", PACKAGE], check=False)
    if os.name == "nt":
        # The shortcut was created on the desktop Windows reports, which
        # OneDrive commonly redirects; also sweep the unredirected location
        # in case an older run of this script put it there. Shortcuts are
        # matched by target rather than by name -- the user may have renamed
        # ours -- and only ones pointing at this installation are deleted: a
        # shortcut to some other cadnano2 is not ours to remove.
        desktops = {
            windows_desktop_dir(),
            Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop",
        }
        for desktop in desktops:
            if not desktop.is_dir():
                continue
            for lnk, lnk_target in desktop_shortcuts(desktop):
                if shortcut_points_at_install(lnk_target, bin_dir):
                    try:
                        lnk.unlink()
                        info(f"Removed {lnk}")
                    except OSError as exc:
                        warn(f"could not remove {lnk}: {exc}")
                elif lnk.stem.lower().startswith(COMMAND):
                    if JAPANESE_UI:
                        info(f"{lnk} は残しました: このインストールを指していないため")
                    else:
                        info(f"Left {lnk} in place: it does not point at this installation")
    remaining = other_installations(bin_dir)
    if remaining:
        info("")
        if JAPANESE_UI:
            info(f"注意: このスクリプトが入れたものではない別の {COMMAND} が PATH 上に")
            info("残っています(こちらには手を付けていません):")
        else:
            info(f"Note: another {COMMAND} remains on PATH, not installed by this")
            info("script and left untouched:")
        for other in remaining:
            info(f"    {other}")
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
        version = subprocess.run(
            [uv, "--version"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if version.returncode == 0:
            info(f"uv version:    {version.stdout.strip()}")
        info(f"system certs:  --system-certs uses {system_certs_variable(uv)}")
        bin_dir = tool_bin_dir(uv)
        on_path = "yes" if already_on_path(bin_dir) else "NO"
        info(f"tool bin dir:  {bin_dir}   [on PATH: {on_path}]")
        if os.name == "nt":
            persisted = windows_path_contains(windows_user_path(), bin_dir)
            info(f"user PATH:     {'registered' if persisted else 'NOT registered'}")
            if persisted and on_path == "NO":
                info("               (open a new Command Prompt to pick it up)")
        listing = subprocess.run(
            [uv, "tool", "list"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        installed = [
            line for line in (listing.stdout or "").splitlines() if line.startswith(PACKAGE)
        ]
        info(f"{PACKAGE}:      {installed[0] if installed else 'not installed'}")

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
    if uv:
        report_command_conflicts(bin_dir)


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
    # The launchers already announce which uv they found; repeating it here
    # would print the line twice, so it is shown only on a direct run.
    if not os.environ.get("CADNANO_LAUNCHER"):
        info(f"Using uv at {uv}")

    install_cadnano2(
        uv, args.python, args.system_certs, args.insecure, args.reinstall, args.upgrade
    )
    patch_documentwindow(uv)
    patch_launch_guard(uv)

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
    report_command_conflicts(bin_dir)

    info("")
    info("Done. Open a new terminal, then start cadnano2 by running:")
    info(f"    {COMMAND}")
    if os.name == "nt":
        info("A new Command Prompt is required: open windows keep the old PATH.")
        info("You can also double-click the cadnano2 shortcut on your desktop.")


if __name__ == "__main__":
    main()
