import re
import errno
import hashlib


def slugify(value: str) -> str:
    """Convert a string to a filesystem-safe slug."""
    value = str(value)
    value = re.sub(r"[^a-zA-Z0-9_.+-]+", "_", value)
    return re.sub(r"[_-]+", "_", value).strip("_")


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


def get_base_name(name: str) -> str:
    """Generate a consistent base filename from name."""
    md = hashlib.md5()
    md.update(name.encode())
    return f"{slugify(name)[:24]}_{md.hexdigest()[:24]}"
