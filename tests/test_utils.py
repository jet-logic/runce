import pytest
from runce.utils import slugify, get_base_name


def test_slugify():
    assert slugify("Hello World!") == "Hello_World"
    assert slugify("test@example.com") == "test_example.com"
    assert slugify("  extra  spaces  ") == "extra_spaces"
    assert slugify("special!@#$%^&*()chars") == "special_chars"
    # assert slugify("unicode-éèê") == "unicode_e_e_e"


def test_get_base_name():
    name1 = get_base_name("test")
    name2 = get_base_name("test")
    name3 = get_base_name("different")

    assert name1 == name2  # Same input produces same output
    assert name1 != name3  # Different input produces different output
    assert len(name1) <= 24 + 1 + 24  # Max length check
