#!/bin/sh
# Bootstrap installer for cadnano2 on macOS, Linux and other Unix systems.
#
# uv, not Python, is what this repository actually depends on: uv supplies the
# interpreter cadnano2 runs on. Starting from `python3 setup.py` inverts that
# order, because a Python has to already exist before the script that installs
# uv can run at all -- on a clean Mac that means downloading the Xcode Command
# Line Tools purely to reach the installer. This script restores the order: uv
# first, then setup.py handed to `uv run`, which brings its own Python.
#
# Arguments are passed straight through to setup.py:
#     ./install.sh --check
#     ./install.sh --upgrade

set -eu

INSTALLER_URL="https://astral.sh/uv/install.sh"

# Resolved rather than assumed to be the working directory, so the script also
# works when it is invoked by path from somewhere else.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SETUP="$SCRIPT_DIR/setup.py"

# User-facing dialogs are shown in Japanese on a Japanese locale; routine
# output stays English. setup.py makes the same decision for its own dialogs.
JA=""
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in ja*) JA=1 ;; esac

fail() {
    printf 'error: %s\n' "$1" >&2
    exit 1
}

find_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi
    # The official installer obeys these variables, so a uv installed under one
    # of them sits outside the default directory and would otherwise look
    # missing. Empty variables collapse to a bare "/bin", which is skipped.
    for dir in \
        "${UV_INSTALL_DIR:-}" \
        "${XDG_BIN_HOME:-}" \
        "${CARGO_HOME:-}/bin" \
        "${HOME:-}/.local/bin" \
        "${HOME:-}/.cargo/bin"
    do
        case $dir in "" | "/bin" | "/.local/bin" | "/.cargo/bin") continue ;; esac
        if [ -x "$dir/uv" ]; then
            printf '%s\n' "$dir/uv"
            return 0
        fi
    done
    return 1
}

fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl -fLsS --proto '=https' --tlsv1.2 -o "$2" "$1"
    elif command -v wget >/dev/null 2>&1; then
        # Match the curl branch's TLS posture. A wget without these options
        # (busybox) may skip certificate verification entirely, so refuse it
        # rather than run an installer fetched over an unverified connection.
        # -nv keeps errors visible, unlike -q which silences them.
        if wget --help 2>&1 | grep -q -- --https-only; then
            wget -nv --https-only --secure-protocol=TLSv1_2 -O "$2" "$1"
        elif [ -n "$JA" ]; then
            fail "この wget は証明書検証付き HTTPS を強制できないため中止しました。
curl をインストールして再実行してください。"
        else
            fail "this wget cannot enforce verified HTTPS; install curl and re-run"
        fi
    else
        fail "neither curl nor wget is available to download the uv installer"
    fi
}

install_uv() {
    # The official installer honours these variables; report the directory it
    # will actually use rather than hardcoding the default.
    uv_dest="${UV_INSTALL_DIR:-${XDG_BIN_HOME:-${HOME:-~}/.local/bin}}"
    cat <<END

========================================================================
uv was not found on this system, so it will be installed now.

  what      uv, the package manager used to install cadnano2
  source    $INSTALLER_URL  (official installer, Astral)
  where     $uv_dest
  rights    no administrator privileges required

The installer also adds $uv_dest to your shell configuration.
To skip this step, install uv yourself and re-run:
    curl -LsSf $INSTALLER_URL | sh
========================================================================

END

    tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/cadnano-uv.XXXXXX")
    trap 'rm -rf "$tmpdir"' EXIT INT TERM

    # Downloaded to a file first rather than piped straight into a shell, so a
    # truncated download cannot be executed halfway.
    if ! fetch "$INSTALLER_URL" "$tmpdir/install.sh"; then
        if [ -n "$JA" ]; then
            fail "uv インストーラーをダウンロードできませんでした:
    $INSTALLER_URL"
        else
            fail "could not download the uv installer from:
    $INSTALLER_URL"
        fi
    fi
    [ -s "$tmpdir/install.sh" ] || fail "the downloaded uv installer was empty"
    printf 'Downloaded installer (%s bytes).\n' "$(wc -c <"$tmpdir/install.sh" | tr -d ' ')"

    sh "$tmpdir/install.sh"

    rm -rf "$tmpdir"
    trap - EXIT INT TERM
}

[ -f "$SETUP" ] || fail "setup.py was not found next to this script ($SETUP)"

uv=$(find_uv || true)
if [ -z "$uv" ]; then
    install_uv
    # Looked up again rather than assumed: the installer writes ~/.local/bin
    # into the shell configuration, which this already-running shell will not
    # pick up, so the fresh uv is reachable by path only.
    uv=$(find_uv || true)
fi
[ -n "$uv" ] || fail "the uv installer reported success, but uv could not be found.
Open a new terminal, which will pick up the updated PATH, and re-run this script."

printf 'Using uv at %s\n' "$uv"

# --script keeps uv from treating a surrounding directory as a project and
# makes it honour the requires-python line in setup.py's inline metadata.
exec "$uv" run --script "$SETUP" "$@"
