#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import csv
import shlex
import sys
import os
import socket
import getpass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class VirtualFileSystem:
    def __init__(self, csv_path=None):
        self.root = {"type": "dir", "children": {},
                     "permissions": 0o755, "data": None}
        self.current = []
        self.source = None
        if csv_path is not None:
            self.load(csv_path)

    def load(self, path):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Файл не найден: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError(f"Не удалось прочитать файл: {e}")

        if not rows:
            raise ValueError("Пустой CSV-файл")

        required = {"type", "name", "parent", "permissions", "data"}
        if not required.issubset(rows[0].keys()):
            raise ValueError("Неверный формат CSV: пропущены колонки")

        new_root = {"type": "dir", "children": {},
                    "permissions": 0o755, "data": None}

        for i, row in enumerate(rows, start=2):
            try:
                self._insert(new_root, row)
            except ValueError as e:
                raise ValueError(f"Ошибка в строке {i}: {e}")

        self.root = new_root
        self.current = []
        self.source = path

    def _insert(self, root, row):
        typ = row["type"].strip()
        name = row["name"].strip()
        parent = row["parent"].strip()
        try:
            perms = int(row["permissions"], 8)
        except ValueError:
            raise ValueError(f"неверные права: {row['permissions']}")

        if typ not in ("dir", "file"):
            raise ValueError(f"неизвестный тип: {typ}")

        node = {"type": typ, "permissions": perms}
        if typ == "file":
            raw = (row.get("data") or "").strip()
            if raw:
                try:
                    node["data"] = base64.b64decode(raw)
                except Exception:
                    raise ValueError(f"некорректный base64: {raw!r}")
            else:
                node["data"] = b""
            node["children"] = None
        else:
            node["children"] = {}
            node["data"] = None

        parent_node = self._find(root, parent)
        if parent_node is None:
            raise ValueError(f"родитель не найден: {parent}")
        if parent_node["type"] != "dir":
            raise ValueError(f"родитель не каталог: {parent}")

        parent_node["children"][name] = node

    def _find(self, root, path):
        if path in ("/", ""):
            return root
        components = [c for c in path.split("/") if c]
        node = root
        for c in components:
            if node["type"] != "dir":
                return None
            if c not in node["children"]:
                return None
            node = node["children"][c]
        return node

    @property
    def current_path(self):
        if not self.current:
            return "/"
        return "/" + "/".join(self.current)

    def resolve(self, path):
        if path in ("", "~"):
            return []
        if path.startswith("/"):
            components = []
        else:
            components = list(self.current)
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if components:
                    components.pop()
            else:
                components.append(part)
        return components

    def get_node(self, components):
        node = self.root
        for part in components:
            if node["type"] != "dir":
                return None
            if part not in node["children"]:
                return None
            node = node["children"][part]
        return node

    def count(self):
        def _walk(node):
            if node["type"] == "dir":
                return 1 + sum(
                    _walk(c) for c in node["children"].values()
                )
            return 1
        return _walk(self.root)

    def describe(self):
        if self.source:
            return f"VFS загружена из: {self.source}"
        return "VFS по умолчанию (пустая)"


class EmulatorConfig:
    def __init__(self, vfs_path=None, script_path=None):
        self.vfs_path = vfs_path
        self.script_path = script_path

    def debug_print(self):
        print("=" * 40)
        print("Конфигурация эмулятора:")
        vfs = self.vfs_path or "не указан"
        script = self.script_path or "не указан"
        print(f"  Путь к VFS:                {vfs}")
        print(f"  Путь к стартовому скрипту: {script}")
        print("=" * 40)
        print()


def get_prompt():
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"[{username}@{hostname}]$ "


def parse_command(line):
    try:
        return shlex.split(line)
    except ValueError as e:
        print(f"Ошибка разбора: {e}")
        return []


def cmd_ls(args, vfs):
    print(f"ls: команда-заглушка. Аргументы: {args}")
    return True


def cmd_cd(args, vfs):
    print(f"cd: команда-заглушка. Аргументы: {args}")
    return True


def cmd_vfs_info(args, vfs):
    print(vfs.describe())
    print(f"Текущая директория: {vfs.current_path}")
    print(f"Всего элементов: {vfs.count()}")
    return True


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "vfs-info": cmd_vfs_info,
}


def execute_command(command, args, vfs):
    if command == "exit":
        return True
    if command in COMMANDS:
        return COMMANDS[command](args, vfs)
    print(f"Эмулятор: команда не найдена: {command}")
    return False


def run_script(script_path, vfs, prompt):
    if not os.path.isfile(script_path):
        print(f"Ошибка: скрипт не найден: {script_path}")
        return

    print(f"Выполнение стартового скрипта: {script_path}\n")

    errors = 0
    with open(script_path, "r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, start=1):
            line = raw.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue

            print(f"{prompt}{line}")
            parts = parse_command(line)
            if not parts:
                print(f"Ошибка в строке {line_num}")
                errors += 1
                continue

            command = parts[0]
            args = parts[1:]

            if command == "exit":
                print("Выход из эмулятора.")
                sys.exit(0)

            if not execute_command(command, args, vfs):
                print(f"Ошибка в строке {line_num}")
                errors += 1

    print()
    if errors:
        print(f"Скрипт завершён с ошибками: {errors}")
    else:
        print("Скрипт выполнен успешно.")


def repl(vfs, prompt):
    print(f"Добро пожаловать в эмулятор оболочки. "
          f"{vfs.describe()}")
    print("Введите 'exit' для выхода.\n")

    while True:
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not line.strip():
            continue

        parts = parse_command(line)
        if not parts:
            continue

        command = parts[0]
        args = parts[1:]

        if command == "exit":
            print("Выход из эмулятора.")
            break

        execute_command(command, args, vfs)


def main():
    parser = argparse.ArgumentParser(
        description="Эмулятор командной оболочки "
                    "UNIX-подобной ОС (Вариант 18)"
    )
    parser.add_argument(
        "--vfs", type=str, default=None,
        help="Путь к CSV-файлу VFS"
    )
    parser.add_argument(
        "--script", type=str, default=None,
        help="Путь к стартовому скрипту"
    )
    args = parser.parse_args()

    config = EmulatorConfig(vfs_path=args.vfs, script_path=args.script)
    config.debug_print()

    vfs = VirtualFileSystem()
    if args.vfs:
        try:
            vfs.load(args.vfs)
            print(f"VFS успешно загружена: {args.vfs}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Ошибка загрузки VFS: {e}")
            sys.exit(1)
    else:
        print("VFS не указана, используется пустая по умолчанию.")

    prompt = get_prompt()

    if args.script:
        run_script(args.script, vfs, prompt)

    repl(vfs, prompt)


if __name__ == "__main__":
    main()