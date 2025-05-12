import logging
from json import dump, load
from uuid import uuid4
from pathlib import Path
from subprocess import DEVNULL, STDOUT, Popen
from time import time
from .utils import generate_pseudowords, get_base_name, look_multiple


class Spawn:
    """Process spawner with singleton enforcement."""

    data_dir: Path

    def __getattr__(self, name: str) -> object:
        if not name.startswith("_get_"):
            f = getattr(self, f"_get_{name}", None)
            if f:
                setattr(self, name, None)
                v = f()
                setattr(self, name, v)
                return v
        try:
            m = super().__getattr__
        except AttributeError:
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            ) from None
        else:
            return m(name)

    def _get_data_dir(self):
        from pathlib import Path
        from tempfile import gettempdir

        return Path(gettempdir()) / "runce.v1"

    def spawn(
        self,
        cmd: list[str] = [],
        name: str = "",
        split: bool = False,
        overwrite: bool = False,
        out_file: str = "",
        err_file: str = "",
        in_file: str = "",
        **po_kwa,
    ):
        """Spawn a new singleton process."""

        uuid = str(uuid4())
        if name:
            base_name = get_base_name(name)
        else:
            name = base_name = generate_pseudowords(3, 3)
        data_dir = self.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)

        mode = "w" if overwrite else "x"

        if in_file:
            po_kwa["stdin"] = Path(in_file).open("rb")

        if not cmd:
            cmd = ["sh"]
            if po_kwa.get("stdin") is None:
                from sys import stdin

                po_kwa["stdin"] = stdin.buffer

        if split:
            so = Path(out_file) if out_file else data_dir / f"{base_name}.out.log"
            se = Path(err_file) if err_file else data_dir / f"{base_name}.err.log"
            po_kwa["stdout"] = so.open(f"{mode}b")
            po_kwa["stderr"] = se.open(f"{mode}b")
        else:
            so = se = Path(out_file) if out_file else data_dir / f"{base_name}.log"
            po_kwa["stdout"] = so.open(f"{mode}b")
            po_kwa["stderr"] = STDOUT

        po_kwa.setdefault("start_new_session", True)
        po_kwa.setdefault("close_fds", True)
        po_kwa.setdefault("stdin", DEVNULL)

        process_info = {
            "out": str(so),
            "err": str(se),
            "cmd": cmd,
            "name": name or uuid,
            "started": time(),
            "uuid": uuid,
        }

        process_info["base_name"] = base_name
        process_info["pid"] = Popen(cmd, **po_kwa).pid
        # print("PI", process_info)
        return self.add_process(process_info)

    def add_process(self, process_info: dict[str, object]):
        """Insert a new process record."""
        # print(process_info)
        run_file = self.data_dir / f"{process_info['base_name']}.run.json"
        with run_file.open("x") as f:
            dump(process_info, f, indent=True)

        return process_info

    def all(self):
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
                        d: dict[str, int | str] = load(f)
                        d["file"] = str(child)
                        yield d
                except Exception as e:
                    logging.exception(f"Load failed {child!r} {e!s}")

    def find_name(self, name: str):
        """Find a process by name"""
        for x in self.all():
            if x["name"] == name:
                return x
        return None

    def drop(self, entry: dict[str, object], clean_up=True):
        """Clean up files associated with a process."""
        from os.path import isfile
        from os import remove

        for k in ("out", "err", "file"):
            v = entry.get(k)
            if v and isfile(v):
                if clean_up or k == "file":
                    remove(v)

    def find_names(
        self, names: list[str], ambiguous=lambda x: None, not_found=lambda x: None
    ):
        if names:
            yield from look_multiple(names, self.all(), ambiguous, not_found)
        else:
            yield from self.all()
