#!/bin/bash
# Тестирование этапа 5
# Вариант 18

export PYTHONIOENCODING=utf-8

PY="python -u src/main.py"
if command -v winpty >/dev/null 2>&1; then
    PY="winpty python -u src/main.py"
fi

run() {
    local desc="$1"
    shift
    echo "=== $desc ==="
    $PY "$@"
    echo ""
}

run "1. VFS с файлами и subdir" \
    --vfs vfs_samples/vfs_files.csv \
    --script start_scripts/stage5_commands.txt

run "2. Минимальная VFS" \
    --vfs vfs_samples/vfs_minimal.csv \
    --script start_scripts/stage5_commands.txt

run "3. Глубокая VFS" \
    --vfs vfs_samples/vfs_deep.csv \
    --script start_scripts/stage5_commands.txt

read -p "Нажмите Enter, чтобы закрыть..."