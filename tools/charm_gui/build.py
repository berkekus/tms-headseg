"""Build the launcher on the target OS; never bundles SimNIBS or MRI data."""

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def main():
    if sys.platform not in ("darwin", "win32"):
        raise SystemExit("Build on macOS or Windows; cross-compilation is not supported.")
    root = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["PYINSTALLER_CONFIG_DIR"] = str(root / ".build-cache")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir",
               "--name", "CHARM Launcher", "--distpath", str(root / "dist"),
               "--workpath", str(root / ".build"), "--specpath", str(root / ".build")]
    if sys.platform == "darwin":
        command += ["--osx-bundle-identifier", "org.tmsheadseg.charm-launcher"]
    command.append(str(root / "app.py"))
    subprocess.run(command, cwd=root, env=env, check=True)
    dist = root / "dist"
    target = "macos" if sys.platform == "darwin" else "windows"
    archive = dist / f"CHARM-Launcher-{target}-{platform.machine()}.zip"
    if sys.platform == "darwin":
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(dist / "CHARM Launcher.app"), str(archive)], check=True)
    else:
        shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=dist,
                            base_dir="CHARM Launcher")
    print(f"Desktop package: {archive}")


if __name__ == "__main__":
    main()
