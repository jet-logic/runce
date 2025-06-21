from argparse import ArgumentParser
from shlex import join
from sys import stderr, stdout, platform
from subprocess import Popen, PIPE, run
from typing import Any
from .utils import check_pid, filesizepu, kill_pid, tail_bytes
from .main import Main, flag, arg
from .procdb import ProcessDB as Manager

# from .spawn import Spawn as Manager


class FormatDict(dict):
    def __missing__(self, key: str) -> str:
        if key == "pid?":
            return f'{self["pid"]}{"" if check_pid(self["pid"]) else "?"}'
        elif key == "elapsed":
            import time

            return time.strftime("%H:%M:%S", time.gmtime(time.time() - self["started"]))
        elif key == "command":
            if isinstance(self["cmd"], str):
                return self["cmd"]
            return join(self["cmd"])
        elif key == "pid_status":
            return "Live" if check_pid(self["pid"]) else "Done"
        raise KeyError(f"No {key!r}")


def format_prep(f: str):

    def fn(x: "dict[str, Any]") -> str:
        return f.format_map(FormatDict(x))

    return fn


def no_record(name):
    try:
        print("🤷‍ ", end="")
    except UnicodeEncodeError:
        pass
    print(f"No record of {name!r}")


def ambiguous(name):
    try:
        print("⁉️ ", end="")
    except UnicodeEncodeError:
        pass
    print(f"{name!r} is ambiguous")


class Clean(Main):
    """Clean up dead processes."""

    ids: "list[str]" = arg("ID", "run ids", nargs="*")

    def add_arguments(self, argp: ArgumentParser) -> None:
        argp.description = "Clean up entries for non-existing processes"
        return super().add_arguments(argp)

    def start(self) -> None:
        sp = Manager()
        for d in sp.find_names(self.ids, ambiguous, no_record):
            if check_pid(d["pid"]):
                continue
            try:
                print("🧹 ", end="")
            except UnicodeEncodeError:
                pass
            print(f"Cleaning {d['pid']} {d['name']}")
            sp.drop(d)


class Status(Main):
    """Check process status."""

    ids: "list[str]" = arg("ID", "run ids", nargs="*")
    format: str = flag(
        "f",
        "format of entry line",
        default="{pid_status} {elapsed} {pid} {name}, {command}",
    )

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "Check process status"
        return super().init_argparse(argp)

    def start(self) -> None:
        f = format_prep(self.format)
        e = ["✅", "❌"]
        for d in Manager().find_names(self.ids, ambiguous, no_record):
            print(f(d))


class Kill(Main):
    """Kill running processes."""

    ids: "list[str]" = arg("ID", "run ids", nargs="+")
    dry_run: bool = flag("dry-run", "dry run (don't actually kill)", default=False)
    remove: bool = flag("remove", "remove entry after killing", default=False)
    group: bool = flag("group", "kill process group", default=False)
    signal: str = flag("signal", "send signal", default=None)

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "Kill the process of a run id"
        return super().init_argparse(argp)

    def start(self) -> None:
        _errdef = ["❌", "Error"]
        _noproc = ["👻", "No process"]
        _killed = ["💀", "Killed"]
        signal = int(self.signal) if self.signal else None
        sp = Manager()
        if self.ids:
            for x in sp.find_names(self.ids, ambiguous, no_record):
                s = _errdef
                if self.dry_run:
                    s = _killed
                else:
                    if check_pid(x["pid"]):
                        if kill_pid(x["pid"], process_group=self.group):
                            s = _killed
                    else:
                        s = _noproc
                try:
                    print(f"{s[0]} ", end="")
                except UnicodeEncodeError:
                    pass
                print(f'{s[1]} PID={x["pid"]} {x["name"]!r}')
                if not self.dry_run and self.remove:
                    sp.drop(x)


def _tail(n: float, u="", out="", tab=None):
    if u:
        stdout.buffer.write(tail_bytes(out, int(n)))
    elif n > 0:
        if platform.startswith("win"):
            cmd = [
                "powershell",
                "-c",
                f"Get-Content -Tail {int(n)} '{out}'",
            ]
        else:
            cmd = ["tail", "-n", str(int(n)), out]
        if tab:
            with Popen(cmd, stdout=PIPE).stdout as o:
                for line in o:
                    stdout.buffer.write(b"\t" + line)
        else:
            run(cmd)


class Tail(Main):
    """Tail process output."""

    ids: "list[str]" = arg("ID", "run ids", nargs="*")
    format: str = flag("header", "header format")
    lines: str = flag("n", "lines", "how many lines or bytes")
    existing: bool = flag("x", "only-existing", "only show existing processes", default=False)
    tab: bool = flag("t", "tab", "prefix tab space", default=False)
    err: bool = flag("e", "err", "output stderr", default=False)
    p_open: str = "=== "
    p_close: str = " ==="

    def start(self) -> None:

        if self.format == "no":
            hf = None
        else:
            hf = format_prep(self.format or r"{pid?}: {name}")
        n, u = filesizepu(self.lines or "10")
        j = 0
        out = "err" if self.err else "out"

        for x in Manager().find_names(self.ids, ambiguous, no_record):
            if self.existing and not check_pid(x["pid"]):
                continue

            j > 1 and n > 0 and print()
            if hf:
                print(f"{self.p_open}{hf(x)}{self.p_close}", flush=True)
            _tail(n, u, x[out], self.tab)
            j += 1


class Run(Main):
    """Run a new singleton process."""

    args: "list[str]" = arg("ARG", nargs="*", metavar="arg")
    tail: int = flag("t", "tail", "tail the output with n lines", default=0)
    run_id: str = flag("id", "Unique run identifier", default="")
    cwd: str = flag("Working directory for the command")
    tail: str = flag(
        "t",
        "tail",
        "Tail the output (n lines). Use `-t -1` to print the entire output",
        # default=0,
    )
    overwrite: bool = flag("overwrite", "Overwrite existing entry", default=False)
    cmd_after: str = flag("run-after", "Run command after", metavar="command")
    split: bool = flag("split", "Dont merge stdout and stderr", default=False)
    input: str = flag("i", "input", "pass FILE to stdin", metavar="FILE", default="")

    def start(self) -> None:
        args = self.args
        name = self.run_id  # or " ".join(x for x in args)
        sp = Manager()

        # Check for existing process first
        e = sp.find_name(name) if name else None
        if e:
            s = ["🚨", r"Found: PID={pid} ({pid_status}) {name}"]
        else:
            
            # Start new process
            e = sp.spawn(args, name, overwrite=self.overwrite, cwd=self.cwd, split=self.split, in_file=self.input)
            s = ["🚀", r"Started: PID={pid} ({pid_status}) {name}"]
        assert e
        try:
            print(f"{s[0]} ", end="", file=stderr)
        except UnicodeEncodeError:
            pass
        hf = format_prep(s[1])
        print(hf(e), file=stderr, flush=True)

        # Handle tail output
        if self.tail:
            n, u = filesizepu(self.tail)
            _tail(n, u, e["out"])

        # Run post-command if specified
        if self.cmd_after:
            cmd = format_prep(self.cmd_after)(e)
            run(cmd, shell=True, check=True)


class Ls(Main):
    """List all managed processes."""

    format: str = flag(
        "f",
        "format of entry line",
        default="",
    )

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "List all managed processes"
        return super().init_argparse(argp)

    def start(self) -> None:
        f = self.format
        if f:
            pass
        else:
            f = "{pid_status} {elapsed} {pid}\t{name}, {command}"
            print("Stat Elapsed  PID\tName, Command")
            print("---- -------- ------ ------------")
        fp = format_prep(f)
        for d in Manager().all():
            print(fp(d))


class Restart(Main):
    """Restart a process."""

    ids: "list[str]" = arg("ID", "run ids", nargs="+")
    tail: int = flag("t", "tail", "tail the output with n lines", default=0)

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "Restart a process"
        return super().init_argparse(argp)

    def start(self) -> None:
        sp = Manager()
        if self.ids:
            for proc in sp.find_names(self.ids, ambiguous, no_record):
                # First kill existing process
                Kill().main(["--remove", proc["name"]])
                # Then restart with same parameters
                Run().main(["--id", proc["name"], "-t", self.tail, "--", *proc["cmd"]])


class App(Main):
    """Main application class."""

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.prog = "runce"
        argp.description = (
            "Runce (Run Once) - Ensures commands run exactly once.\n" "Guarantees singleton execution per unique ID."
        )
        return super().init_argparse(argp)

    def sub_args(self) -> Any:
        """Register all subcommands."""
        yield Tail(), {"name": "tail", "help": "Tail process output"}
        yield Run(), {"name": "run", "help": "Run a new singleton process"}
        yield Ls(), {"name": "list", "help": "List all processes"}
        yield Clean(), {"name": "clean", "help": "Clean dead processes"}
        yield Status(), {"name": "status", "help": "Check process status"}
        yield Kill(), {"name": "kill", "help": "Kill processes"}
        yield Restart(), {"name": "restart", "help": "Restart processes"}


def main():
    """CLI entry point."""
    App().main()


if __name__ == "__main__":
    main()
