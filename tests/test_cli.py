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
        o = result.stdout + result.stderr
        print(o)
        # if stdout_only:
        #     return result.stdout
        # Combine stdout and stderr for verification
        return o

    def test_split(self):
        o = self.run_runce(
            "run", "--split", "--", "bash", "-c", "echo -n 123; echo -n 456 >&2"
        )
        m = re.search(r"(?mx) \W+ Started: \W+ [^\)]+ \s+ \( [^\)]+ \) \s+ (.+)", o)
        self.assertTrue(m)
        n = m.group(1)
        self.assertTrue(n)
        o = self.run_runce("tail", "--header", "no", n)
        # print(n)
        self.assertEqual(o, "123")
        o = self.run_runce("tail", "--err", "--header", "no", n)
        self.assertEqual(o, "456")
        self.run_runce("kill", n)
        self.run_runce("clean", n)

    def test_cli(self):
        o = self.run_runce("run", "--id", "apple", "--", "bash", "-c", "sleep 10")
        self.assertRegex(o, r"(?xim) \W+ started: \W+ .+ \W+ apple \W+")

        o = self.run_runce(
            "run",
            "--split",
            "--id",
            "banana",
            "--",
            "bash",
            "-c",
            'for ((i=0; i<10; i++)); do echo "banana $i" >&2; sleep 2; done',
        )
        self.assertRegex(o, r"(?xim) \W+ started: \W+ .+ \W+ banana \W+")

        o = self.run_runce(
            "run",
            "--id",
            "pineapple",
            "--",
            "bash",
            "-c",
            'for ((i=0; i<10; i++)); do echo "pineapple $i"; sleep 2; done',
        )
        self.assertRegex(o, r"(?xim) \W+ started: \W+ .+ \W+ pineapple \W+")

        for x in self.run_runce("status").strip().splitlines():
            self.assertRegex(
                x, r"(?xi) \W+ live \W+ .+ \W+ (?:apple|pineapple|banana) \W+"
            )
        o = self.run_runce("tail", "pineapple")
        self.assertRegex(o, r"(?xim) \W+ pineapple \W+ \d+ \W+")

        o = self.run_runce("tail", "--header", "no", "banana")
        self.assertEqual(o, "")

        # o = self.run_runce("tail", "--err", "banana")

        o = self.run_runce("run", "--id", "banana", "--", "bash", "-c", "sleep 10")
        self.assertRegex(o, r"(?xim) \W+ found \W+ .+ \W+ banana \W+")

        o = self.run_runce("kill", "app")
        self.assertRegex(o, r"(?xim) \W+ app \W+ is \W+ ambiguous")

        o = self.run_runce("kill", "apple")
        self.assertRegex(o, r"(?xim) killed .+ \W+ apple \W+")

        for x in self.run_runce("kill", "lemon", "banana").strip().splitlines():
            self.assertRegex(
                x,
                r"(?xim) \W+ no \s+ record .+ \W+ lemon \W+ | \W+ killed .+ \W+ banana \W+",
            )
        o = self.run_runce("restart", "banana")
        # self.assertRegex()

        for x in self.run_runce("status").strip().splitlines():
            self.assertRegex(
                x,
                r"(?xi) \W+ live \W+ .+ \W+ (?:pineapple|banana) | gone \W+ .+ \W+ apple \W+",
            )
            pass

        self.assertRegex(
            self.run_runce("clean", "apple"), r"(?xim)^ \W+ Cleaning \W+ .+ \W+ apple"
        )
        self.run_runce("list")
        for x in self.run_runce("kill", "--remove", "pi", "b").strip().splitlines():
            self.assertRegex(x, r"(?xi) killed .+ \W+ (?:pineapple|banana) \W+")


if __name__ == "__main__":
    main()
