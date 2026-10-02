#!/bin/bash
# Тестирование параметров командной строки эмулятора
# Вариант 18, этап 2

export PYTHONIOENCODING=utf-8

PY="python -u src/main.py"
if command -v winpty >/dev/null 2>&1; then
    PY="winpty python -u src/main.py"
fi

echo "=== 1. Без параметров ==="
echo "exit" | $PY

echo ""
echo "=== 2. Только VFS ==="
echo "exit" | $PY --vfs ./vfs_samples

echo ""
echo "=== 3. Только стартовый скрипт ==="
$PY --script start_scripts/stage2_commands.txt

echo ""
echo "=== 4. Оба параметра ==="
$PY --vfs ./vfs_samples \
    --script start_scripts/stage2_commands.txt

echo ""
echo "=== 5. Несуществующий стартовый скрипт ==="
$PY --script ./no_such_script.txt