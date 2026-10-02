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

## Этап 3. VFS
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

## Коммиты
Сообщения в стиле Conventional Commits.