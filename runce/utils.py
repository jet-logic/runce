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


import random


def uuid_to_phonetic_words(uuid_obj, word_count=4):
    """Generate phonetic pseudowords from UUID"""
    # Phoneme categories
    onsets = [
        "bl",
        "br",
        "cl",
        "cr",
        "dr",
        "fl",
        "fr",
        "gl",
        "gr",
        "pl",
        "pr",
        "sc",
        "sh",
        "sk",
        "sl",
        "sm",
        "sn",
        "sp",
        "st",
        "sw",
        "th",
        "tr",
        "tw",
        "wh",
        "wr",
    ]
    vowels = [
        "a",
        "e",
        "i",
        "o",
        "u",
        "ai",
        "au",
        "aw",
        "ay",
        "ea",
        "ee",
        "ei",
        "eu",
        "ew",
        "ey",
        "ie",
        "oa",
        "oi",
        "oo",
        "ou",
        "ow",
        "oy",
    ]
    codas = [
        "ct",
        "ft",
        "ld",
        "lf",
        "lk",
        "lm",
        "lp",
        "lt",
        "mp",
        "nd",
        "ng",
        "nk",
        "nt",
        "pt",
        "rb",
        "rd",
        "rf",
        "rg",
        "rk",
        "rl",
        "rm",
        "rn",
        "rp",
        "rt",
        "rv",
        "sk",
        "sp",
        "ss",
        "st",
        "tt",
    ]

    random.seed(uuid_obj.int)
    words = []
    for _ in range(word_count):
        # Build syllable: onset + vowel + coda
        syllable = random.choice(onsets) if random.random() > 0.3 else ""
        syllable += random.choice(vowels)
        syllable += random.choice(codas) if random.random() > 0.5 else ""

        # Sometimes add a second syllable
        if random.random() > 0.7:
            syllable += random.choice(vowels) + (
                random.choice(codas) if random.random() > 0.5 else ""
            )

        words.append(syllable)

    return "-".join(words)


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
    ambiguous: Callable[[str], Any] = lambda x: None,
    not_found: Callable[[str], Any] = lambda x: None,
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
