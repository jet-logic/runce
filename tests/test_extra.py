from pathlib import Path
from unittest import TestCase, main
from runce.procdb import ProcessDB
from runce.spawn import Spawn
from runce.utils import slugify, get_base_name, look
from subprocess import PIPE, run
import re


class TestUtils(TestCase):

    def run_runce(self, *args, stdout_only=False):
        """Helper to run python -m runce with stderr capture"""
        cmd = ["python", "-m", "runce", *args]
        print("RUN:", *cmd)
        result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
        if stdout_only:
            return result.stdout
        # Combine stdout and stderr for verification
        return result.stdout + result.stderr

    def test_split(self):
        o = self.run_runce(
            "run", "--split", "--", "bash", "-c", "echo -n 123; echo -n 456 >&2"
        )
        m = re.search(r"(?m)\s+Started:\s+[^\)]+\s+\([^\)]+\)\s+(.+)", o)
        self.assertTrue(m)
        self.assertTrue(m.group(1))
        o = self.run_runce("tail", "--header", "no", m.group(1))
        print(m.group(1))
        self.assertEqual(o, "123")
        o = self.run_runce("tail", "--err", "--header", "no", m.group(1))
        self.assertEqual(o, "456")
        self.run_runce("clean")

    def test_ambi(self):
        o = self.run_runce("run", "--id", "apple", "--", "bash", "-c", "sleep 10")
        o = self.run_runce("run", "--id", "banana", "--", "bash", "-c", "sleep 10")
        o = self.run_runce("run", "--id", "pineapple", "--", "bash", "-c", "sleep 10")
        self.assertRegex(
            self.run_runce("kill", "app"), r"(?xim) \W+ app \W+ is \W+ ambiguous"
        )
        self.assertRegex(
            self.run_runce("kill", "apple"), r"(?xim) killed .+ \W+ apple \W+"
        )
        o = self.run_runce("kill", "pi", "b")
        self.assertRegex(o, r"(?xim) killed .+ \W+ pineapple \W+")
        self.assertRegex(o, r"(?xim) killed .+ \W+ banana \W+")


if __name__ == "__main__":
    main()
