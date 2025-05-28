import os
from pathlib import Path
from signal import SIGINT
import subprocess
import tempfile
from time import sleep
from unittest import TestCase, main
from runce.procdb import ProcessDB
from runce.spawn import Spawn
from runce.utils import kill_pid, slugify, get_base_name, look, tail_bytes


class TestUtils(TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Hello World!"), "Hello_World")
        self.assertEqual(slugify("test@example.com"), "test_example.com")
        self.assertEqual(slugify("  extra  spaces  "), "extra_spaces")
        self.assertEqual(slugify("special!@#$%^&*()chars"), "special_chars")
        # self.assertEqual(slugify("unicode-éèê"), "unicode_e_e_e")  # Uncomment if unicode handling is expected

    def test_get_base_name(self):
        name1 = get_base_name("test")
        name2 = get_base_name("test")
        name3 = get_base_name("different")

        self.assertEqual(name1, name2)
        self.assertNotEqual(name1, name3)
        self.assertLessEqual(len(name1), 49)  # Max length check

    def test_spawn_data_dir(self):
        sp = Spawn()
        self.assertTrue(sp.data_dir.parent.exists())

    def test_look(self):
        db = [
            dict(name="apple"),
            dict(name="banana"),
            dict(name="carrot"),
            dict(name="carpet"),
        ]
        self.assertIs(look("carpet", db), db[3])
        self.assertIs(look("car", db), False)
        self.assertIs(look("carr", db), db[2])
        self.assertIs(look("e", db), False)
        self.assertIs(look("le", db), db[0])
        self.assertIs(look("citrus", db), None)
        self.assertIs(look("b", db), db[1])

    def test_tail_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp)
            zero = top / "zero.txt"
            zero.touch()

            self.assertEqual(tail_bytes(str(zero), 1000), b"")
            file = top / "file.txt"
            file.write_bytes(b"content")
            self.assertEqual(tail_bytes(str(file), 6), b"ontent")
            self.assertEqual(tail_bytes(str(file), 8), b"content")
            self.assertEqual(tail_bytes(str(file), 7), b"content")

    def test_spawn_echo(self):
        pdb = ProcessDB()
        if os.name == "nt":
            kw = {"creationflags": subprocess.CREATE_NO_WINDOW}
        else:
            kw = {}

        p = pdb.spawn(
            [
                "python",
                "-c",
                'from sys import stderr, stdout; stdout.write("123"); stderr.write("456")',
            ],
            split=True,
            **kw
        )

        sleep(2)
        a = pdb.find_name(p["name"])
        o = Path(a["out"]).read_text()
        e = Path(a["err"]).read_text()
        k = kill_pid(p["pid"])
        print(k, a)
        self.assertTrue(a)
        self.assertEqual(o, "123")
        self.assertRegex(e, r"\A456\W?\Z")
        self.assertIsNone(pdb.find_name("!@#"))
        b = pdb.spawn(
            [
                "python",
                "-c",
                "from sys import stdin, stdout; stdout.write(stdin.read())",
            ],
            split=True,
            in_file=a["err"],
            **kw
        )
        pdb.drop(p)
        sleep(2)
        o = Path(b["out"]).read_text()
        e = Path(b["err"]).read_text()
        kill_pid(b["pid"])
        pdb.drop(b)
        self.assertEqual(e, "", b["name"])
        self.assertRegex(o, r"\A456\W?\Z", b["name"])


if __name__ == "__main__":
    main()
