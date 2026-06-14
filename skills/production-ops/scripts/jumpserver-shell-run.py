#!/usr/bin/env python3
import argparse
import locale
import os
import re
import sys
import time

import paramiko


def read_all(chan, delay=1.0):
    time.sleep(delay)
    chunks = []
    while chan.recv_ready():
        chunks.append(chan.recv(65535))
        time.sleep(0.15)
    data = b"".join(chunks)
    for encoding in ("utf-8", locale.getpreferredencoding(False) or "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def send(chan, command, delay=2.0, echo=True):
    chan.send(command + "\r")
    out = read_all(chan, delay)
    if echo:
        print(f"--- {command} ---")
        print(out)
    return out


def strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\].*?\x07", "", text)


def main():
    parser = argparse.ArgumentParser(description="Run commands on a host selected from a JumpServer shell menu.")
    parser.add_argument("--jump-host", default=os.environ.get("JUMP_HOST", "192.168.1.100"))
    parser.add_argument("--port", type=int, default=12222)
    parser.add_argument("--user", required=True)
    parser.add_argument("--key", required=True, help="PEM/OpenSSH private key path")
    parser.add_argument("--target", required=True, help="Target host search text, e.g. 10.0.0.3")
    parser.add_argument("--target-id", default="1", help="ID to select after search; default 1")
    parser.add_argument("--command", action="append", help="Command to run after logging into the target host")
    parser.add_argument("--command-file", help="Read one shell command per line from a UTF-8 text file")
    parser.add_argument("--width", type=int, default=220)
    parser.add_argument("--height", type=int, default=100)
    args = parser.parse_args()

    commands = list(args.command or [])
    if args.command_file:
        with open(args.command_file, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.rstrip("\r\n").lstrip("\ufeff")
                if not line.strip():
                    continue
                if line.lstrip().startswith("#"):
                    continue
                commands.append(line)

    if not commands:
        raise SystemExit("At least one command is required.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        args.jump_host,
        port=args.port,
        username=args.user,
        key_filename=args.key,
        timeout=15,
        banner_timeout=30,
        auth_timeout=30,
        look_for_keys=False,
        allow_agent=False,
    )

    chan = client.invoke_shell(width=args.width, height=args.height)
    initial = read_all(chan, 2)
    print(strip_ansi(initial))
    search_out = send(chan, f"/{args.target}", 2)
    clean = strip_ansi(search_out)
    if args.target not in clean:
        print(f"Target search output did not contain {args.target!r}; review selection before write operations.", file=sys.stderr)
    send(chan, args.target_id, 5)

    for command in commands:
        send(chan, command, 4)

    chan.close()
    client.close()


if __name__ == "__main__":
    main()
