@echo off
rem Bootstrap installer for cadnano2 on Windows.
rem
rem uv, not Python, is what this repository actually depends on: uv supplies
rem the interpreter cadnano2 runs on. Starting from `python setup.py` inverts
rem that order, and Windows has no system Python -- so the old route made users
rem install Python from python.org purely to reach a script whose job is to
rem install uv, which then downloads a Python of its own and leaves two behind.
rem This file restores the order: uv first, then setup.py handed to `uv run`,
rem which brings its own interpreter. Nothing has to be installed beforehand.
rem
rem Double-click it, or run it from a Command Prompt with arguments, which are
rem passed straight through to setup.py:
rem     install.bat --check
rem     install.bat --upgrade

setlocal EnableExtensions

set "INSTALLER_URL=https://astral.sh/uv/install.ps1"
set "SETUP=%~dp0setup.py"
set "UVSCRIPT=%TEMP%\cadnano-uv-install.ps1"
set "EXITCODE=0"
set "UV="

if not exist "%SETUP%" (
    echo error: setup.py was not found next to this script: "%SETUP%" 1>&2
    set "EXITCODE=1"
    goto :end
)

rem Already on PATH?
for /f "delims=" %%I in ('where uv 2^>nul') do if not defined UV set "UV=%%I"

rem Installed, but not yet on this session's PATH. The first two are honoured by
rem the official installer; the rest are where other package managers put it.
if defined UV_INSTALL_DIR call :probe "%UV_INSTALL_DIR%\uv.exe"
if defined XDG_BIN_HOME call :probe "%XDG_BIN_HOME%\uv.exe"
call :probe "%USERPROFILE%\.local\bin\uv.exe"
if defined CARGO_HOME call :probe "%CARGO_HOME%\bin\uv.exe"
call :probe "%USERPROFILE%\.cargo\bin\uv.exe"
if defined LOCALAPPDATA call :probe "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
call :probe "%USERPROFILE%\scoop\shims\uv.exe"

rem Kept on separate lines rather than wrapped in a parenthesised block: cmd.exe
rem expands a whole block before running any of it, so an %EXITCODE% read inside
rem the block would report the value from before :install_uv ran.
if not defined UV call :install_uv
if not "%EXITCODE%"=="0" goto :end

if not defined UV (
    echo error: the uv installer reported success, but uv could not be found. 1>&2
    echo Open a NEW Command Prompt, which will pick up the updated PATH, 1>&2
    echo and run this script again. 1>&2
    set "EXITCODE=1"
    goto :end
)

echo Using uv at "%UV%"
echo(

rem --script keeps uv from treating a surrounding directory as a project and
rem makes it honour the requires-python line in setup.py's inline metadata.
"%UV%" run --script "%SETUP%" %*
set "EXITCODE=%ERRORLEVEL%"
goto :end


:probe
rem Record the first candidate that exists; later calls are no-ops.
if defined UV goto :eof
if exist "%~1" set "UV=%~1"
goto :eof


:install_uv
echo(
echo ========================================================================
echo uv was not found on this system, so it will be installed now.
echo(
echo   what      uv, the package manager used to install cadnano2
echo   source    %INSTALLER_URL%  (official installer, Astral)
echo   where     "%USERPROFILE%\.local\bin"
echo   rights    no administrator privileges required
echo(
echo To skip this step, install uv yourself and run this script again:
echo     powershell -ExecutionPolicy ByPass -c "irm %INSTALLER_URL% | iex"
echo ========================================================================
echo(

rem Downloaded to a file first rather than piped straight into a shell, so a
rem truncated download cannot be executed halfway. The paths are read from the
rem environment inside PowerShell rather than interpolated into the command
rem line, so an apostrophe in the profile path cannot break the quoting.
if exist "%UVSCRIPT%" del /q "%UVSCRIPT%"
rem -Command is not subject to the execution policy, so no Bypass is needed
rem here; the -File run below does need it, because policy governs .ps1 files.
powershell -NoProfile -Command "irm $env:INSTALLER_URL -OutFile $env:UVSCRIPT"
if errorlevel 1 (
    echo error: could not download the uv installer from %INSTALLER_URL% 1>&2
    set "EXITCODE=1"
    goto :eof
)
if not exist "%UVSCRIPT%" (
    echo error: could not download the uv installer from %INSTALLER_URL% 1>&2
    set "EXITCODE=1"
    goto :eof
)
for %%A in ("%UVSCRIPT%") do if %%~zA equ 0 (
    echo error: the downloaded uv installer was empty 1>&2
    del /q "%UVSCRIPT%"
    set "EXITCODE=1"
    goto :eof
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%UVSCRIPT%"
if errorlevel 1 (
    echo error: the uv installer failed 1>&2
    del /q "%UVSCRIPT%"
    set "EXITCODE=1"
    goto :eof
)
del /q "%UVSCRIPT%" >nul 2>&1

rem Looked up again rather than assumed: the installer registers ~\.local\bin
rem in the user PATH, which this already-running Command Prompt will not pick
rem up, so the fresh uv is reachable by full path only.
call :probe "%USERPROFILE%\.local\bin\uv.exe"
if defined UV_INSTALL_DIR call :probe "%UV_INSTALL_DIR%\uv.exe"
if defined XDG_BIN_HOME call :probe "%XDG_BIN_HOME%\uv.exe"
if defined UV echo uv installed at "%UV%"
goto :eof


:end
rem Keep the window open when cmd.exe was started just to run this file --
rem an Explorer double-click, but also PowerShell and Windows Terminal, which
rem launch a fresh `cmd /c` the same way -- because that window closes the
rem moment the batch ends and takes the output with it. Only a batch started
rem from an existing Command Prompt session skips the pause.
set "CMDLINE=%cmdcmdline:"=%"
echo "%CMDLINE%"| find /i "%~nx0" >nul
if not errorlevel 1 (
    echo(
    pause
)
exit /b %EXITCODE%
