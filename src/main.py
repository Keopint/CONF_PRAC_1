import argparse
import base64
import csv
import re
import shlex
import sys
import os
import socket
import getpass
import time
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def mode_to_string(mode):
    chars = []
    for shift in (6, 3, 0):
        bits = (mode >> shift) & 0b111
        chars.append("r" if bits & 4 else "-")
        chars.append("w" if bits & 2 else "-")
        chars.append("x" if bits & 1 else "-")
    return "".join(chars)


def parse_symbolic_mode(current, mode_str):
    result = current
    for clause in mode_str.split(","):
        m = re.match(r"^([ugoa]*)([+\-=])([rwx]*)$", clause)
        if not m:
            return None
        who, op, perm_chars = m.groups()
        if not who:
            who = "a"

        if "a" in who:
            shifts = [6, 3, 0]
        else:
            shifts = []
            for c in who:
                if c == "u":
                    shifts.append(6)
                elif c == "g":
                    shifts.append(3)
                elif c == "o":
                    shifts.append(0)

        bits = 0
        for p in perm_chars:
            if p == "r":
                bits |= 4
            elif p == "w":
                bits |= 2
            elif p == "x":
                bits |= 1
            else:
                return None

        for shift in shifts:
            mask = 0b111 << shift
            if op == "+":
                result |= (bits << shift)
            elif op == "-":
                result &= ~(bits << shift)
            elif op == "=":
                result = (result & ~mask) | (bits << shift)
    return result & 0o777


def parse_chmod_mode(current, mode_str):
    if re.match(r"^[0-7]{1,4}$", mode_str):
        try:
            value = int(mode_str, 8)
        except ValueError:
            return None
        return value & 0o777
    if re.match(
        r"^[ugoa]*[+\-=][rwx]*(,[ugoa]*[+\-=][rwx]*)*$",
        mode_str,
    ):
        return parse_symbolic_mode(current, mode_str)
    return None

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
                rows = list(csv.DictReader(f))
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError(f"Не удалось прочитать файл: {e}")
        if not rows:
            raise ValueError("Пустой CSV-файл")
        required = {"type", "name", "parent",
                    "permissions", "data"}
        if not required.issubset(rows[0].keys()):
            raise ValueError("Неверный формат CSV")
        new_root = {"type": "dir", "children": {},
                    "permissions": 0o755, "data": None}
        for i, row in enumerate(rows, start=2):
            try:
                self._insert(new_root, row)
            except ValueError as e:
                raise ValueError(f"Строка {i}: {e}")
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
            raise ValueError(f"права: {row['permissions']}")
        if typ not in ("dir", "file"):
            raise ValueError(f"тип: {typ}")
        if typ == "file":
            raw = (row.get("data") or "").strip()
            if raw:
                try:
                    data = base64.b64decode(raw)
                except Exception:
                    raise ValueError(f"base64: {raw!r}")
            else:
                data = b""
            node = {"type": "file", "permissions": perms,
                    "children": None, "data": data}
        else:
            node = {"type": "dir", "permissions": perms,
                    "children": {}, "data": None}
        parent_node = self._find(root, parent)
        if parent_node is None:
            raise ValueError(f"родитель: {parent}")
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


class EmulatorState:
    def __init__(self):
        self.start_time = time.time()
        self.history = []

    def add(self, line):
        self.history.append(line)

    def uptime(self):
        return int(time.time() - self.start_time)


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


def get_user_host():
    return f"{getpass.getuser()}@{socket.gethostname()}"


def get_prompt(vfs):
    return f"{get_user_host()}:{vfs.current_path}$ "


def parse_command(line):
    try:
        return shlex.split(line)
    except ValueError as e:
        print(f"Ошибка разбора: {e}")
        return []

def _parse_ls_args(args):
    show_all = False
    long_format = False
    path = None
    for a in args:
        if a in ("-a", "--all"):
            show_all = True
        elif a == "-l":
            long_format = True
        elif a.startswith("-") and len(a) > 1:
            for flag in a[1:]:
                if flag == "a":
                    show_all = True
                elif flag == "l":
                    long_format = True
                else:
                    print(f"ls: неизвестный параметр: -{flag}")
                    return None
        else:
            if path is not None:
                print("ls: слишком много аргументов")
                return None
            path = a
    return show_all, long_format, path


def _print_long(node, name):
    perms = mode_to_string(node.get("permissions", 0o644))
    if node["type"] == "dir":
        print(f"d{perms}  {'<DIR>':>8}  {name}")
    else:
        size = len(node.get("data") or b"")
        print(f"-{perms}  {size:>8}  {name}")


def cmd_ls(args, vfs, state):
    parsed = _parse_ls_args(args)
    if parsed is None:
        return False
    show_all, long_format, path = parsed

    comps = list(vfs.current) if path is None else vfs.resolve(path)
    node = vfs.get_node(comps)
    if node is None:
        print(f"ls: невозможно получить доступ "
              f"к '{path}': Нет такого файла или каталога")
        return False

    if node["type"] == "file":
        if long_format:
            _print_long(node, path or ".")
        else:
            print(path or ".")
        return True

    names = sorted(node["children"].keys())
    if not show_all:
        names = [n for n in names if not n.startswith(".")]
    if not names:
        return True

    if long_format:
        for name in names:
            _print_long(node["children"][name], name)
    else:
        print("  ".join(names))
    return True


def cmd_cd(args, vfs, state):
    if len(args) > 1:
        print("cd: слишком много аргументов")
        return False
    path = args[0] if args else "~"
    comps = vfs.resolve(path)
    node = vfs.get_node(comps)
    if node is None:
        print(f"cd: {path}: Нет такого файла или каталога")
        return False
    if node["type"] != "dir":
        print(f"cd: {path}: Не является каталогом")
        return False
    vfs.current = comps
    return True


def _parse_chmod_args(args):
    recursive = False
    positional = []
    for a in args:
        if a in ("-R", "--recursive"):
            recursive = True
        elif a in ("-h", "--help"):
            print("Использование: chmod [-R] РЕЖИМ ФАЙЛ...")
            print("  РЕЖИМ — числовой (755) "
                  "или символьный (u+x,go-w,a=r)")
            return None
        elif a.startswith("-") and len(a) > 1 \
                and not a[1].isdigit():
            print(f"chmod: неизвестный параметр: {a}")
            return None
        else:
            positional.append(a)

    if len(positional) < 2:
        print("chmod: не указан режим или файл")
        print("Использование: chmod [-R] РЕЖИМ ФАЙЛ...")
        return None

    mode_str = positional[0]
    targets = positional[1:]

    if not _is_valid_mode(mode_str):
        print(f"chmod: неверный режим: '{mode_str}'")
        return None

    return recursive, mode_str, targets


def _is_valid_mode(mode_str):
    if re.match(r"^[0-7]{1,4}$", mode_str):
        return True
    if re.match(
        r"^[ugoa]*[+\-=][rwx]*(,[ugoa]*[+\-=][rwx]*)*$",
        mode_str,
    ):
        return True
    return False


def _apply_mode(node, mode_str):
    current = node.get("permissions", 0o644)
    new_mode = parse_chmod_mode(current, mode_str)
    if new_mode is None:
        return False
    node["permissions"] = new_mode
    return True


def _apply_mode_recursive(node, mode_str):
    ok = _apply_mode(node, mode_str)
    if node["type"] == "dir":
        for child in node["children"].values():
            if not _apply_mode_recursive(child, mode_str):
                ok = False
    return ok


def cmd_chmod(args, vfs, state):
    parsed = _parse_chmod_args(args)
    if parsed is None:
        return False
    recursive, mode_str, targets = parsed

    overall_ok = True
    for target in targets:
        comps = vfs.resolve(target)
        node = vfs.get_node(comps)
        if node is None:
            print(f"chmod: невозможно получить доступ "
                  f"к '{target}': Нет такого файла или каталога")
            overall_ok = False
            continue
        if recursive:
            ok = _apply_mode_recursive(node, mode_str)
        else:
            ok = _apply_mode(node, mode_str)
        if not ok:
            print(f"chmod: неверный режим: '{mode_str}'")
            return False
    return overall_ok


def cmd_uptime(args, vfs, state):
    if args:
        print("uptime: команда не принимает аргументов")
        return False
    sec = state.uptime()
    h = sec // 3600
    m = (sec % 3600) // 60
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f" {now} up {h}:{m:02d}, 1 user, "
          f"load average: 0.00, 0.01, 0.05")
    return True


def cmd_history(args, vfs, state):
    items = list(state.history)
    if items and items[-1].strip().startswith("history"):
        items = items[:-1]
    start = 0
    if args:
        if len(args) > 1:
            print("history: слишком много аргументов")
            return False
        try:
            n = int(args[0])
            if n < 0:
                print("history: число отрицательное")
                return False
            start = max(0, len(items) - n)
        except ValueError:
            print(f"history: неверное число: '{args[0]}'")
            return False
    for i, cmd in enumerate(items[start:], start=start + 1):
        print(f"{i:5d}  {cmd}")
    return True


def cmd_vfs_info(args, vfs, state):
    print(vfs.describe())
    print(f"Текущая директория: {vfs.current_path}")
    print(f"Всего элементов: {vfs.count()}")
    return True


def cmd_help(args, vfs, state):
    print("Доступные команды:")
    print("  ls [-l] [-a] [путь]         — список содержимого")
    print("  cd [путь]                   — смена директории")
    print("  chmod [-R] РЕЖИМ ФАЙЛ...    — права доступа (в памяти)")
    print("  uptime                      — время работы")
    print("  history [N]                 — история команд")
    print("  vfs-info                    — информация о VFS")
    print("  help                        — справка")
    print("  exit                        — выход")
    return True


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "chmod": cmd_chmod,
    "uptime": cmd_uptime,
    "history": cmd_history,
    "vfs-info": cmd_vfs_info,
    "help": cmd_help,
}


def execute_command(command, args, vfs, state):
    if command == "exit":
        return True
    if command in COMMANDS:
        return COMMANDS[command](args, vfs, state)
    print(f"Эмулятор: команда не найдена: {command}")
    return False


def run_script(script_path, vfs, state):
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
            print(f"{get_prompt(vfs)}{line}")
            state.add(line)
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
            if not execute_command(command, args, vfs, state):
                print(f"Ошибка в строке {line_num}")
                errors += 1
    print()
    if errors:
        print(f"Скрипт завершён с ошибками: {errors}")
    else:
        print("Скрипт выполнен успешно.")


def repl(vfs, state):
    print(f"Добро пожаловать в эмулятор оболочки. "
          f"{vfs.describe()}")
    print("Введите 'help' для списка команд.\n")

    while True:
        try:
            line = input(get_prompt(vfs))
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not line.strip():
            continue
        state.add(line)
        parts = parse_command(line)
        if not parts:
            continue
        command = parts[0]
        args = parts[1:]
        if command == "exit":
            print("Выход из эмулятора.")
            break
        execute_command(command, args, vfs, state)


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

    config = EmulatorConfig(vfs_path=args.vfs,
                            script_path=args.script)
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
        print("VFS не указана, используется пустая.")

    state = EmulatorState()

    if args.script:
        run_script(args.script, vfs, state)

    repl(vfs, state)


if __name__ == "__main__":
    main()