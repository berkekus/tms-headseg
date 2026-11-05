"""Desktop entry point with local startup logs and visible failures."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback


def show_error(message):
    if sys.platform == "darwin":
        try:
            subprocess.run(["/usr/bin/osascript", "-e",
                'on run argv\n display alert "MRI Workbench" message (item 1 of argv) as critical\nend run',
                message], check=True, capture_output=True, timeout=10)
            return
        except (OSError, subprocess.SubprocessError):
            pass
        if sys.stderr is not None:
            print(message, file=sys.stderr)
    elif os.name == "nt":
        ctypes.windll.user32.MessageBoxW(0, message, "MRI Workbench", 0x10)
    elif sys.stderr is not None:
        print(message, file=sys.stderr)


def log_directory():
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "TMSHeadSeg"
    return Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "TMSHeadSeg" / "logs"


def launch():
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    log_path = None
    try:
        folder = log_directory()
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        log_path = folder / f"workbench-{stamp}-{os.getpid()}.log"
        with log_path.open("x", encoding="utf-8", buffering=1) as log:
            with redirect_stdout(log), redirect_stderr(log):
                print(f"MRI Workbench startup. Python: {sys.executable}")
                print(f"Project: {root}")
                try:
                    os.chdir(root)
                    sys.path.insert(0, str(here))
                    from prototype import main
                    main()
                except SystemExit as error:
                    if error.code not in (None, 0):
                        traceback.print_exc()
                        raise RuntimeError(f"Workbench exited with status {error.code}") from error
                except Exception:
                    traceback.print_exc()
                    raise
        return 0
    except Exception as error:
        details = f"Startup log: {log_path}" if log_path else "A startup log could not be created."
        show_error(f"MRI Workbench could not start.\n\n{error}\n\n{details}")
        return 1


if __name__ == "__main__":
    raise SystemExit(launch())
