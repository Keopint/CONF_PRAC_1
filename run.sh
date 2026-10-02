#!/bin/bash
export PYTHONIOENCODING=utf-8

# winpty нужен только в Git Bash на Windows
if command -v winpty >/dev/null 2>&1; then
    winpty python -u src/main.py "$@"
else
    python -u src/main.py "$@"
fi