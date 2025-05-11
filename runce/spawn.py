import logging
from json import dump, load
from uuid import uuid4
from pathlib import Path
from subprocess import DEVNULL, STDOUT, Popen
from time import time
from typing import Any, Dict
from .config import Config
from .utils import get_base_name


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
        out_file: str = "",
        err_file: str = "",
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
                        d: Dict[str, int | str] = load(f)
                        d["file"] = str(child)
                        yield d
                except Exception as e:
                    logging.exception(f"Load failed {child!r}")
