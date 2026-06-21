import json
from pathlib import Path
from ctf_harness_app.util import (
    utc_now,
    read_json,
    write_json,
    tail_text,
    slugify,
    unique_path,
    extract_flag_candidates,
    HarnessError,
)
import pytest


def test_utc_now():
    now = utc_now()
    assert isinstance(now, str)
    # Format: YYYY-MM-DDTHH:MM:SSZ
    assert len(now) == 20
    assert now.endswith("Z")
    assert "T" in now


def test_slugify():
    assert slugify("Simple Name") == "simple-name"
    assert slugify("  Name with   spaces  ") == "name-with-spaces"
    assert slugify("Category/Challenge! Name@123") == "category-challenge-name-123"
    assert slugify("abc---def") == "abc-def"
    assert slugify("...dot_underscore-dash...") == "dot_underscore-dash"
    assert slugify("") == "challenge"


def test_unique_path(tmp_path):
    base_file = tmp_path / "test.txt"
    # Doesn't exist, should return base path
    assert unique_path(base_file) == base_file

    # Create it
    base_file.touch()
    path2 = unique_path(base_file)
    assert path2 == tmp_path / "test-2.txt"

    # Create test-2.txt
    path2.touch()
    path3 = unique_path(base_file)
    assert path3 == tmp_path / "test-3.txt"


def test_read_write_json(tmp_path):
    file_path = tmp_path / "test.json"
    default_val = {"default": True}
    
    # Reading non-existent file returns default
    assert read_json(file_path, default_val) == default_val

    # Write data
    data = {"key": "value", "list": [1, 2, 3]}
    write_json(file_path, data)
    assert file_path.exists()

    # Read written data
    read_data = read_json(file_path, None)
    assert read_data == data

    # Malformed JSON raises HarnessError
    file_path.write_text("invalid json")
    with pytest.raises(HarnessError):
        read_json(file_path, None)


def test_tail_text(tmp_path):
    file_path = tmp_path / "log.txt"
    assert tail_text(file_path) == ""

    content = "line 1\nline 2\nline 3\n"
    file_path.write_bytes(content.encode("utf-8"))

    assert tail_text(file_path, limit=9) == "2\nline 3\n"
    assert tail_text(file_path, limit=1000) == content




def test_extract_flag_candidates():
    text = "Flag is CTF{abcd_1234_efgh} and another CTF{xyz} and short ctf{123}."
    candidates = extract_flag_candidates(text)
    assert "CTF{abcd_1234_efgh}" in candidates
    assert "CTF{xyz}" not in candidates  # less than 4 chars inside braces
    assert "ctf{123}" not in candidates  # less than 4 chars and lower case ctf matches but braces length check is 4+
    
    # Test deduping and limits
    many_flags = " ".join(f"FLAG{{flag_{i}}}" for i in range(15))
    candidates_many = extract_flag_candidates(many_flags)
    assert len(candidates_many) == 10
    assert candidates_many[0] == "FLAG{flag_0}"
    assert candidates_many[-1] == "FLAG{flag_9}"
