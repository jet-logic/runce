import signal
from argparse import ArgumentParser
from subprocess import Popen, PIPE, run
from typing import List, Dict, Any, Optional
from sys import stderr, stdout
from os import getpgid, killpg
from shlex import join
from shutil import copyfileobj
from .spawn import Spawn
from .utils import check_pid
from .main import Main, flag, arg


class FormatDict(dict):
    def __missing__(self, key: str) -> str:
        if key == "pid?":
            return f'{self["pid"]}{"" if check_pid(self["pid"]) else "?👻"}'
        elif key == "elapsed":
            import time

            return time.strftime("%H:%M:%S", time.gmtime(time.time() - self["started"]))
        elif key == "command":
            if isinstance(self["cmd"], str):
                return self["cmd"]
            return join(self["cmd"])
        elif key == "pid_status":
            return "✅ Running" if check_pid(self["pid"]) else "👻 Absent"
        raise KeyError(f"No {key!r}")

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return super().__call__(*args, **kwds)


def format_prep(f: str):

    def fn(x: Dict[str, Any]) -> str:
        return f.format_map(FormatDict(x))

    return fn


def no_record(name):
    print(f"🤷‍♂️ No record of {name!r}")


def ambiguous(name):
    print(f"⁉️ {name!r} is ambiguous")


class Clean(Main):
    """Clean up dead processes."""

    ids: list[str] = arg("ID", "run ids", nargs="*")

    def add_arguments(self, argp: ArgumentParser) -> None:
        argp.description = "Clean up entries for non-existing processes"
        return super().add_arguments(argp)

    def start(self) -> None:
        sp = Spawn()
        for d in sp.find_names(self.ids, ambiguous, no_record):
            if check_pid(d["pid"]):
                continue
            print(f"🧹 Cleaning {d['pid']} {d['name']}")
            sp.drop(d)


class Status(Main):
    """Check process status."""

    ids: list[str] = arg("ID", "run ids", nargs="*")
    format: str = flag(
        "f",
        "format of entry line",
        default="{pid}\t{name}\t{pid_status}\t{elapsed}\t{command}",
    )

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "Check if run id process still exists"
        return super().init_argparse(argp)

    def start(self) -> None:
        f = format_prep(self.format)
        for d in Spawn().find_names(self.ids, ambiguous, no_record):
            print(f(d))


class Kill(Main):
    """Kill running processes."""

    ids: list[str] = arg("ID", "run ids", nargs="+")
    dry_run: bool = flag("dry-run", "dry run (don't actually kill)", default=False)
    remove: bool = flag("remove", "remove entry after killing", default=False)

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "Kill the process of a run id"
        return super().init_argparse(argp)

    def start(self) -> None:
        sp = Spawn()
        if self.ids:
            for x in sp.find_names(self.ids, ambiguous, no_record):
                pref = "❌ Error"
                try:
                    pgid = getpgid(x["pid"])
                    if not self.dry_run:
                        killpg(pgid, signal.SIGTERM)
                    pref = "💀 Killed"
                except ProcessLookupError:
                    pref = "👻 Not found"
                finally:
                    print(f'{pref} {x["pid"]} {x["name"]!r}')
                    if not self.dry_run and self.remove:
                        sp.drop(x)


class Tail(Main):
    """Tail process output."""

    ids: list[str] = arg("ID", "run ids", nargs="*")
    format: str = flag("header", "header format")
    lines: int = flag("n", "lines", "how many lines")
    existing: bool = flag(
        "x", "only-existing", "only show existing processes", default=False
    )
    tab: bool = flag("t", "tab", "prefix tab space", default=False)
    err: bool = flag("e", "err", "oputput the stderr", default=False)
    p_open: str = "📜 "
    p_close: str = ""

    def start(self) -> None:
        if self.format == "no":
            hf = None
        else:
            hf = format_prep(self.format or r"{pid?}: {name}")
        lines = self.lines or 10
        j = 0
        out = "err" if self.err else "out"

        for x in Spawn().find_names(self.ids, ambiguous, no_record):
            if self.existing and not check_pid(x["pid"]):
                continue

            j > 1 and lines > 0 and print()
            if hf:
                print(f"{self.p_open}{hf(x)}{self.p_close}", flush=True)

            if lines > 0:
                # TODO: pythonify
                cmd = ["tail", "-n", str(lines), x[out]]
                if self.tab:
                    with Popen(cmd, stdout=PIPE).stdout as o:
                        for line in o:
                            stdout.buffer.write(b"\t" + line)
                else:
                    run(cmd)
                stdout.flush()
            j += 1


class Run(Main):
    """Run a new singleton process."""

    args: list[str] = arg("ARG", nargs="*", metavar="arg")
    run_id: str = flag("id", "unique run identifier (required)")
    cwd: str = flag("working directory")
    tail: int = flag("t", "tail", "tail the output with n lines", default=0)
    overwrite: bool = flag("overwrite", "overwrite existing entry", default=False)
    cmd_after: str = flag("run-after", "run command after", metavar="command")
    split: bool = flag("split", "dont merge stdout and stderr", default=False)

    def start(self) -> None:
        args = self.args
        name = self.run_id or " ".join(x for x in args)
        sp = Spawn()

        # Check for existing process first
        e = sp.find_name(name)
        if e:
            hf = format_prep(r"🚨 Found: {name} PID:{pid}({pid_status})")
            print(hf(e), file=stderr)
        else:
            # Start new process
            e = sp.spawn(
                args, name, overwrite=self.overwrite, cwd=self.cwd, split=self.split
            )
            hf = format_prep(r"🚀 Started: {name} PID:{pid}({pid_status})")
            print(hf(e), file=stderr)
        assert e

        # Handle tail output
        if self.tail:
            if self.tail < 0:
                with open(e["out"], "rb") as f:
                    copyfileobj(f, stdout.buffer)
            elif self.tail > 0:
                run(["tail", "-n", str(self.tail), e["out"]])

        # Run post-command if specified
        if self.cmd_after:
            cmd = format_prep(self.cmd_after)(e)
            run(cmd, shell=True, check=True)


class Ls(Main):
    """List all managed processes."""

    format: str = flag(
        "f",
        "format of entry line",
        default="{pid}\t{name}\t{pid_status}\t{elapsed}\t{command}",
    )

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "List all managed processes"
        return super().init_argparse(argp)

    def start(self) -> None:
        f = format_prep(self.format)
        print("PID\tName\tStatus\tElapsed\tCommand")
        print("───\t────\t──────\t───────\t───────")
        for d in Spawn().all():
            print(f(d))


class Restart(Main):
    """Restart a process."""

    ids: list[str] = arg("ID", "run ids", nargs="+")
    tail: int = flag("t", "tail", "tail the output with n lines", default=0)

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.description = "Restart a process"
        return super().init_argparse(argp)

    def start(self) -> None:
        sp = Spawn()
        if self.ids:
            for proc in sp.find_names(self.ids, ambiguous, no_record):
                # First kill existing process
                Kill().main(["--remove", proc["name"]])
                # Then restart with same parameters
                Run().main(["--id", proc["name"], "-t", self.tail, *proc["cmd"]])


class App(Main):
    """Main application class."""

    def init_argparse(self, argp: ArgumentParser) -> None:
        argp.prog = "runce"
        argp.description = (
            "Runce (Run Once) - Ensures commands run exactly once.\n"
            "Guarantees singleton execution per unique ID."
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
