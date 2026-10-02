# Эмулятор командной оболочки ОС (Вариант 18)

## Описание
Поэтапная разработка эмулятора командной оболочки UNIX-подобной ОС.

## Запуск
```bash
./run.sh [--vfs ПУТЬ.csv] [--script ПУТЬ]
```

- `--vfs` — путь к CSV-файлу VFS.
- `--script` — путь к стартовому скрипту.

## Формат CSV для VFS
```csv
type,name,parent,permissions,data
dir,/,/,755,
file,readme.txt,/,644,SGVsbG8=
dir,subdir,/,755,
file,nested.txt,/subdir,644,bmVzdGVk
```

Колонки:
- `type` — `dir` или `file`;
- `name` — имя элемента;
- `parent` — путь к родительской директории (`/` — корень);
- `permissions` — восьмеричные права;
- `data` — содержимое файла в base64 (для директорий пусто).

## VFS
- VFS загружается из CSV-файла в память.
- Двоичные данные хранятся в base64.
- Ошибки загрузки: файл не найден, неверный формат,
  родитель не существует, некорректный base64.
- Образцы VFS: `vfs_samples/vfs_minimal.csv`,
  `vfs_samples/vfs_files.csv`, `vfs_samples/vfs_deep.csv`.

## Тестирование
```bash
bash scripts/test_emulator.sh
```

## Основные команды
- `ls [-l] [-a] [путь]` — список содержимого директории VFS.
  - `-l` — длинный формат (тип, права, размер, имя);
  - `-a` — показывать скрытые файлы (с точкой).
- `cd [путь]` — смена директории внутри VFS.
  - Поддерживает `/`, `.`, `..`, `~`, относительные пути.
- `uptime` — реальное время работы эмулятора в формате
  `HH:MM:SS up H:MM, 1 user, load average: ...`.
- `history [N]` — история команд. С `N` — последние N.

### Пример

```
[user@host]$ ls -l /subdir
-rw-r--r--         7  nested.txt

[user@host]$ cd /subdir
[user@host]$ uptime
 14:32:15 up 0:02, 1 user, load average: 0.00, 0.01, 0.05

[user@host]$ history 2
    1  cd /subdir
    2  uptime
```