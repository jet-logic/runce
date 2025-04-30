import signal
import logging
from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, STDOUT, DEVNULL, PIPE, run
from typing import List, Dict, Any, Optional
from sys import exit, stderr, stdout
from os import EX_UNAVAILABLE, getpgid, killpg
from shlex import join
from shutil import copyfileobj
from json import dump, load
from uuid import uuid4
from time import time

from .utils import check_pid, get_base_name, slugify
from .config import Config
from .main import Main, flag, arg


class Spawn:
    """Process spawner with singleton enforcement."""

    def __init__(self):
        self.config = Config()
        self.data_dir = self.config.data_dir

    def spawn(
        self,
        cmd: list[str] = [],
        name: str = "",
        merged_output: bool = True,
        overwrite: bool = False,
        out_file: Optional[str] = None,
        err_file: Optional[str] = None,
        **po_kwa,
    ) -> Dict[str, Any]:
        """Spawn a new singleton process."""
        self.config.ensure_data_dir()
        base_name = get_base_name(name)
        data_dir = self.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)

        run_file = data_dir / f"{base_name}.run.json"
        mode = "w" if overwrite else "x"

        po_kwa.setdefault("start_new_session", True)
        po_kwa.setdefault("close_fds", True)
        po_kwa["stdin"] = DEVNULL

        if not cmd:
            from sys import stdin

            cmd = ["sh"]
            po_kwa["stdin"] = stdin.buffer

        if merged_output:
            so = se = Path(out_file) if out_file else data_dir / f"{base_name}.log"
            po_kwa["stdout"] = so.open(f"{mode}b")
            po_kwa["stderr"] = STDOUT
        else:
            so = Path(out_file) if out_file else data_dir / f"{base_name}.out.log"
            se = Path(err_file) if err_file else data_dir / f"{base_name}.err.log"
            po_kwa["stdout"] = so.open(f"{mode}b")
            po_kwa["stderr"] = se.open(f"{mode}b")

        process_info = {
            "out": str(so),
            "err": str(se),
            "cmd": cmd,
            "name": name,
            "started": time(),
            "uuid": str(uuid4()),
        }

        process_info["pid"] = Popen(cmd, **po_kwa).pid

        with run_file.open(mode) as f:
            dump(process_info, f, indent=True)

        return process_info

    def all(self) -> Any:
        """Yield all managed processes."""
        if not self.data_dir.is_dir():
            return

        for child in self.data_dir.iterdir():
            if (
                child.is_file()
                and child.name.endswith(".run.json")
                and child.stat().st_size > 0
            ):
                try:
                    with child.open() as f:
                        d: Dict[str, Any] = load(f)
                        d["file"] = str(child)
                        yield d
                except Exception as e:
                    logging.exception(f"Load failed {child!r}")


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


def _find(id: str, runs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find a process by ID or partial match."""
    for x in runs:
        if x["name"] == id:
            return x
    for x in runs:
        if id in x["name"]:
            return x
    return None


def _search(sp: Spawn, ids: list[str], not_found: Optional[Any] = None) -> Any:
    """Search for processes by IDs."""
    if ids:
        runs = list(sp.all())
        for n in ids:
            x = _find(n, runs)
            if x:
                runs.remove(x)
                yield x
            else:
                if not_found:
                    not_found(n)
    else:
        yield from sp.all()


def _drop(entry: Dict[str, Any]) -> None:
    """Clean up files associated with a process."""
    from os.path import isfile
    from os import remove

    for k in ("out", "err", "file"):
        v = entry.get(k)
        if v and isfile(v):
            remove(v)


def no_record(name):
    print(f"🤷‍♂️ No record of {name!r}")


class Clean(Main):
    """Clean up dead processes."""

    ids: list[str] = arg("ID", "run ids", nargs="*")

    def add_arguments(self, argp: ArgumentParser) -> None:
        argp.description = "Clean up entries for non-existing processes"
        return super().add_arguments(argp)

    def start(self) -> None:

        for d in _search(Spawn(), self.ids, no_record):
            if check_pid(d["pid"]):
                continue
            print(f"🧹 Cleaning {d['pid']} {d['name']}")
            _drop(d)


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
        for d in _search(Spawn(), self.ids, no_record):
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
        for x in _search(sp, self.ids, no_record):
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
                    _drop(x)


class Tail(Main):
    """Tail process output."""

    ids: list[str] = arg("ID", "run ids", nargs="*")
    format: str = flag("header", "header format")
    lines: int = flag("n", "lines", "how many lines")
    existing: bool = flag(
        "x", "only-existing", "only show existing processes", default=False
    )
    tab: bool = flag("t", "tab", "prefix tab space", default=False)
    p_open: str = "📜 "
    p_close: str = ""

    def start(self) -> None:
        if self.format == "no":
            hf = None
        else:
            hf = format_prep(self.format or r"{pid?}: {name}")
        lines = self.lines or 10
        j = 0

        for x in _search(Spawn(), self.ids, no_record):
            if self.existing and not check_pid(x["pid"]):
                continue

            j > 1 and lines > 0 and print()
            if hf:
                print(f"{self.p_open}{hf(x)}{self.p_close}", flush=True, file=stderr)

            if lines > 0:
                # TODO: pythonify
                cmd = ["tail", "-n", str(lines), x["out"]]
                if self.tab:
                    with Popen(cmd, stdout=PIPE).stdout as o:
                        for line in o:
                            stdout.buffer.write(b"\t" + line)
                else:
                    run(cmd)

            j += 1


class Run(Main):
    """Run a new singleton process."""

    args: list[str] = arg("ARG", nargs="*", metavar="arg")
    run_id: str = flag("id", "unique run identifier (required)")
    cwd: str = flag("working directory")
    tail: int = flag("t", "tail", "tail the output with n lines", default=0)
    overwrite: bool = flag("overwrite", "overwrite existing entry", default=False)
    cmd_after: str = flag("run-after", "run command after", metavar="command")

    def start(self) -> None:
        args = self.args
        name = self.run_id or " ".join(x for x in args)
        sp = Spawn()

        # Check for existing process first
        e = _find(name, list(sp.all()))
        if e:
            hf = format_prep(r"🚨 Found: {name} PID:{pid}({pid_status})")
            print(hf(e), file=stderr)
        else:
            # Start new process
            e = sp.spawn(args, name, overwrite=self.overwrite, cwd=self.cwd)
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
        for proc in _search(Spawn(), self.ids, no_record):
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
