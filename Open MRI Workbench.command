#!/bin/bash
# Finder entry point. Use only the project's existing desktop environment.
set -u

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
PYTHON="$ROOT/tools/mri_prototype/.venv/bin/python"
LAUNCHER="$ROOT/tools/mri_prototype/launch.py"

pause_on_error() {
    if [ -t 0 ]; then
        printf '\nPress Return to close this window. '
        read -r _
    fi
}

if [ ! -x "$PYTHON" ]; then
    printf '%s\n' 'The MRI Workbench environment is missing or cannot run.' \
        'Complete the macOS setup in tools/mri_prototype/README.md first.' >&2
    pause_on_error
    exit 1
fi
if [ ! -f "$LAUNCHER" ]; then
    printf '%s\n' 'The Workbench launcher is missing. Keep this file in the project root.' >&2
    pause_on_error
    exit 1
fi

cd -- "$ROOT" || exit 1
"$PYTHON" "$LAUNCHER" "$@"
status=$?
if [ "$status" -ne 0 ]; then
    printf '%s\n' 'MRI Workbench could not start or exited with an error. Check the startup message and log.' >&2
    pause_on_error
fi
exit "$status"
