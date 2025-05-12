from pathlib import Path
from unittest import TestCase, main
from runce.procdb import ProcessDB
from runce.spawn import Spawn
from runce.utils import slugify, get_base_name, look


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

    def test_spawn_echo(self):
        pdb = ProcessDB()
        p = pdb.spawn(["bash", "-c", "echo -n 123; echo -n 456 >&2"], split=True)
        a = pdb.find_name(p["name"])
        self.assertTrue(a)
        self.assertEqual(Path(a["out"]).read_text(), "123")
        self.assertEqual(Path(a["err"]).read_text(), "456")
        self.assertIsNone(pdb.find_name("!@#"))
        b = pdb.spawn(["cat", "-"], split=True, in_file=a["err"])
        self.assertEqual(Path(b["out"]).read_text(), "456", b["name"])
        self.assertEqual(Path(b["err"]).read_text(), "", b["name"])


if __name__ == "__main__":
    main()
