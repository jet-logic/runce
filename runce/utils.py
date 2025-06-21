import os
import re
import errno
import hashlib
import signal
from sys import stderr
from typing import List, Dict, Iterator, Callable, Any, Optional


def slugify(value: str) -> str:
    """Convert a string to a filesystem-safe slug."""
    value = str(value)
    value = re.sub(r"[^a-zA-Z0-9_.+-]+", "_", value)
    return re.sub(r"[_-]+", "_", value).strip("_")


if os.name == "nt":  # Windows
    import ctypes

    def check_pid(pid: int) -> bool:
        """Properly checks if a process is running by verifying exit code."""
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        # STILL_ACTIVE exit code (259)
        STILL_ACTIVE = 0x103

        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False

        try:
            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)

    def kill_pid(pid: int, sig: Optional[int] = None, process_group: Optional[bool] = None) -> bool:
        try:
            os.kill(pid, signal.SIGTERM if sig is None else sig)
        except PermissionError as e:
            if check_pid(pid) is False:
                return False
        except OSError as e:
            if 87 == getattr(e, "winerror", 0):  # ERROR_INVALID_PARAMETER (no such process)
                return False
            raise
        return True

else:

    def check_pid(pid: int) -> bool:
        """Check if a Unix process exists."""
        try:
            from os import kill

            kill(pid, 0)
        except OSError as err:
            if err.errno == errno.ESRCH:  # No such process
                return False
            elif err.errno == errno.EPERM:  # Process exists
                return True
            raise
        return True

    def kill_pid(
        pid: int,
        sig: Optional[int] = signal.SIGTERM,
        process_group: Optional[bool] = None,
    ) -> bool:
        try:
            if process_group:
                os.killpg(pid, sig)
            else:
                os.kill(pid, sig)
            return True
        except OSError as e:
            if e.errno == errno.ESRCH:  # No such process/group
                return False
            raise


def get_base_name(name: str) -> str:
    """Generate a consistent base filename from name."""
    md = hashlib.md5()
    md.update(name.encode())
    return f"{slugify(name)[:24]}_{md.hexdigest()[:24]}"


import random


def look(id: str, runs: "list[dict[str, object]]"):
    """Find by 'name' or partial match."""
    m = None
    for x in runs:
        if x["name"] == id:
            return x
        elif id in x["name"]:
            if m is not None:
                return False  # more than one partial match
            m = x
    return m


def look_multiple(
    ids: "list[str]",
    runs: "list[dict[str, Any]]",
    ambiguous: "Callable[[str], Any]" = lambda x: None,
    not_found: "Callable[[str], Any]" = lambda x: None,
) -> Iterator[Dict[str, Any]]:
    map_ids = dict([(id, ([], [])) for id in ids])
    for item in runs:
        name = item["name"]
        for id, (exact, partial) in map_ids.items():
            if name == id:
                exact.append(item)
            elif id in name:
                partial.append(item)
    for id, (exact, partial) in map_ids.items():
        if exact:
            if len(exact) > 1:
                ambiguous(id)
            elif len(exact) > 0:
                yield exact[0]
        elif partial:
            if len(partial) > 1:
                ambiguous(id)
            elif len(partial) > 0:
                yield partial[0]
        else:
            not_found(id)


def generate_pseudowords(word_count=4, syllables_per_word=2):
    """Generate pronounceable pseudowords using syllable patterns"""
    consonants = "bcdfghjklmnpqrstvwxyz"
    vowels = "aeiou"

    words = []
    for _ in range(word_count):
        word = []
        for _ in range(syllables_per_word):
            # Choose random syllable pattern (CV, VC, or CVC)
            pattern = random.choice(["cv", "vc", "cvc"])
            syllable = ""
            for char in pattern:
                if char == "c":
                    syllable += random.choice(consonants)
                else:
                    syllable += random.choice(vowels)
            word.append(syllable)
        words.append("".join(word))

    return "-".join(words)


def tail_file(filename="", n=10):
    """Efficiently reads last 'n' lines (like Unix 'tail')."""
    with open(filename, "rb") as f:
        # Seek to end, then step backwards to find line breaks
        f.seek(0, 2)  # Move to EOF
        end = f.tell()  # Get EOF position
        line_count = 0
        pos = end - 1  # Start at last byte

        while pos >= 0 and line_count < n:
            f.seek(pos)
            char = f.read(1)
            if char == b"\n":
                line_count += 1
            pos -= 1

        f.seek(pos + 2)  # Rewind to start of last line
        return f.read().splitlines()[-n:]


def filesizepu(s: str) -> tuple[int, str]:
    u = ""
    if s[0].isnumeric() or s[0].startswith("."):
        q = s.lower()
        if q.endswith("b"):
            q, u = q[0:-1], q[-1]
        for i, v in enumerate("kmgtpezy"):
            if q[-1].endswith(v):
                return int(float(q[0:-1]) * (2 ** (10 * (i + 1)))), v
        return int(q), u
    return int(s), u


def tail_bytes(filename: str, num_bytes: int):
    # print("tail_bytes", filename, num_bytes, open(filename, "rb").read(), file=stderr)
    with open(filename, "rb") as f:
        # Seek to the end of the file, then back `num_bytes` (or start of file)
        f.seek(0, 2)  # 2 means seek relative to the end
        file_size = f.tell()
        if file_size < num_bytes:
            f.seek(0)  # If file is smaller than num_bytes, read entire file
            return f.read()
        else:
            f.seek(-num_bytes, 2)  # Seek backwards `num_bytes` from end
            return f.read(num_bytes)
