import sys
import shlex
import socket
import getpass


def get_prompt() -> str:
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"[{username}@{hostname}]$ "


def parse_command(line: str) -> list:
    try:
        return shlex.split(line)
    except ValueError as e:
        print(f"Ошибка разбора: {e}")
        return []


def cmd_ls(args: list) -> bool:
    print(f"ls: команда-заглушка. Аргументы: {args}")
    return True


def cmd_cd(args: list) -> bool:
    print(f"cd: команда-заглушка. Аргументы: {args}")
    return True


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
}


def execute_command(command: str, args: list) -> bool:
    if command == "exit":
        return True
    if command in COMMANDS:
        return COMMANDS[command](args)
    print(f"Эмулятор: команда не найдена: {command}")
    return False


def repl() -> None:
    prompt = get_prompt()
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


def main() -> None:
    repl()


if __name__ == "__main__":
    main()