"""Find SimNIBS and resolve its generated launchers without a command shell."""

import locale
from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
import sys


def find_charm(platform=None):
    platform = platform or sys.platform
    found = shutil.which("charm")
    if found:
        return found
    if platform == "win32":
        roots = [Path.home()]
        for key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            if os.environ.get(key):
                roots.append(Path(os.environ[key]))
        if os.environ.get("LOCALAPPDATA"):
            roots.append(Path(os.environ["LOCALAPPDATA"]) / "Programs")
        pattern = "SimNIBS*/bin/charm.cmd"
    else:
        roots = [Path.home() / "Applications", Path("/Applications")]
        pattern = "SimNIBS*/bin/charm"
    candidates = [file for root in roots for file in root.glob(pattern) if file.is_file()]
    return str(max(candidates, key=lambda p: p.stat().st_mtime)) if candidates else ""


def command_prefix(launcher):
    launcher = Path(launcher)
    if launcher.suffix.lower() not in (".cmd", ".bat"):
        return [str(launcher)]
    try:
        raw = launcher.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode(locale.getencoding())
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Cannot read the SimNIBS wrapper: {error}") from error
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pattern = r'(?:start "Loading SimNIBS"\s+)?"([^"\r\n]+)"\s+-E\s+-u\s+"([^"\r\n]+)"\s+%\*'
    match = re.fullmatch(pattern, lines[1], flags=re.IGNORECASE) if len(lines) == 2 and lines[0].lower() == "@echo off" else None
    if not match:
        raise ValueError("Unsupported SimNIBS wrapper. Select the original bin/charm.cmd from a standard SimNIBS installation.")
    python, script = map(Path, match.groups())
    if (python.name.lower() not in ("python.exe", "pythonw.exe")
            or not python.is_absolute() or not script.is_absolute()
            or not python.is_file() or not script.is_file()):
        raise ValueError("The SimNIBS installation referenced by this wrapper is missing or moved. Repair SimNIBS or select its current launcher.")
    return [str(python), "-E", "-u", str(script)]


def external_environment():
    env = os.environ.copy()
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        root = Path(bundle).absolute()
        roots = [root, root.resolve()]
        if root.parent.name == "Contents":
            roots.append(root.parent)
        for key in ("PATH", "DYLD_LIBRARY_PATH", "LD_LIBRARY_PATH", "QT_PLUGIN_PATH",
                    "QT_QPA_PLATFORM_PLUGIN_PATH", "PYTHONHOME", "PYTHONPATH"):
            if key in env:
                kept = [part for part in env[key].split(os.pathsep)
                        if not any(Path(part).absolute().is_relative_to(base)
                                   or Path(part).resolve().is_relative_to(base) for base in roots)]
                if kept:
                    env[key] = os.pathsep.join(kept)
                else:
                    env.pop(key)
    return env


@contextmanager
def external_runtime():
    # PyInstaller's DLL directory must not override the external SimNIBS runtime.
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        import win32api
        original = win32api.GetDllDirectory()
        win32api.SetDllDirectory(None)
        try:
            yield
        finally:
            win32api.SetDllDirectory(original)
    else:
        yield
