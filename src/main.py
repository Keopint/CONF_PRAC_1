import argparse
import shlex
import sys
import os
import socket
import getpass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


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


def cmd_ls(args):
    print(f"ls: команда-заглушка. Аргументы: {args}")
    return True


def cmd_cd(args):
    print(f"cd: команда-заглушка. Аргументы: {args}")
    return True


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
}


def execute_command(command, args):
    if command == "exit":
        return True
    if command in COMMANDS:
        return COMMANDS[command](args)
    print(f"Эмулятор: команда не найдена: {command}")
    return False


def run_script(script_path, prompt):
    if not os.path.isfile(script_path):
        print(f"Ошибка: скрипт не найден: {script_path}")
        return

    print(f"Выполнение стартового скрипта: {script_path}\n")

    errors = 0
    with open(script_path, "r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, start=1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.strip().startswith("#"):
                continue

            print(f"{prompt}{line}")
            parts = parse_command(line)
            if not parts:
                print(f"Ошибка в строке {line_num}: пустая команда")
                errors += 1
                continue

            command = parts[0]
            args = parts[1:]

            if command == "exit":
                print("Выход из эмулятора.")
                sys.exit(0)

            ok = execute_command(command, args)
            if not ok:
                print(f"Ошибка в строке {line_num}: "
                      f"команда завершилась неудачно")
                errors += 1

    print()
    if errors:
        print(f"Скрипт завершён с ошибками: {errors}")
    else:
        print("Скрипт выполнен успешно.")


def repl(prompt):
    print(f"Добро пожаловать в эмулятор оболочки. {prompt}")
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

        execute_command(command, args)


def main():
    parser = argparse.ArgumentParser(
        description="Эмулятор командной оболочки "
                    "UNIX-подобной ОС (Вариант 18)"
    )
    parser.add_argument(
        "--vfs", type=str, default=None,
        help="Путь к физическому расположению VFS"
    )
    parser.add_argument(
        "--script", type=str, default=None,
        help="Путь к стартовому скрипту"
    )
    args = parser.parse_args()

    config = EmulatorConfig(vfs_path=args.vfs, script_path=args.script)
    config.debug_print()

    prompt = get_prompt()

    if args.script:
        run_script(args.script, prompt)

    repl(prompt)


if __name__ == "__main__":
    main()