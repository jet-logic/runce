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


# windows
# import psutil
# def pid_exists(pid):
#     return psutil.pid_exists(pid)


def get_base_name(name: str) -> str:
    """Generate a consistent base filename from name."""
    md = hashlib.md5()
    md.update(name.encode())
    return f"{slugify(name)[:24]}_{md.hexdigest()[:24]}"


def look(id: str, runs: list[dict[str, object]]):
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


from typing import List, Dict, Iterator, Callable, Any


def look_multiple(
    ids: List[str],
    runs: List[Dict[str, Any]],
    multiple_matches: Callable[[str], Any] = lambda x: None,
    not_found: Callable[[str], Any] = lambda x: None,
) -> Iterator[Dict[str, Any]]:
    """Yield matches for multiple IDs with single iteration through runs.

    Args:
        ids: List of names or partial names to search for
        runs: List of dictionaries with "name" keys to search through
        multiple_matches: Callback for IDs with ambiguous matches
        not_found: Callback for IDs with no matches

    Yields:
        Dictionaries from runs that match the search criteria
    """
    # Convert to set for faster lookups and modification
    map_ids = dict([(id, ([], [])) for id in ids])
    for item in runs:

        name = item["name"]

        # Check for exact matches first
        for id, (exact, partial) in map_ids.items():
            if name == id:
                exact.append(item)
            elif id in name:
                partial.append(item)
    # print("###", exact_ids, partial_ids, map_ids)

    for id, (exact, partial) in map_ids.items():
        if exact:
            if len(exact) > 1:
                multiple_matches(id)
            elif len(exact) > 0:
                yield exact[0]
        elif partial:
            if len(partial) > 1:
                multiple_matches(id)
            elif len(partial) > 0:
                yield partial[0]
        else:
            not_found(id)
