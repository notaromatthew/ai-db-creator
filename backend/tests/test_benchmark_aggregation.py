import json
import sqlite3
from pathlib import Path

from aggregate_benchmark import duplicate_rate_for_db


def _mkdb(root: Path, project_id: str) -> Path:
    (root / project_id).mkdir(parents=True, exist_ok=True)
    db = root / project_id / "database.sqlite"
    return db


def test_duplicate_rate_zero_for_unique_pk_rows(tmp_path):
    db = _mkdb(tmp_path, "p1")
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO t VALUES (1,'a'),(2,'b')")
    con.commit()
    con.close()
    assert duplicate_rate_for_db(tmp_path, "p1") == 0.0


def test_duplicate_rate_counts_dup_groups_in_no_pk_table(tmp_path):
    db = _mkdb(tmp_path, "p2")
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE t (code TEXT, v TEXT)")
    con.execute("INSERT INTO t VALUES ('X','a'),('X','a'),('Y','b'),('Y','c')")
    con.commit()
    con.close()
    # tables without a declared PK are not scored (protocol 6.2: duplicate
    # rate = rows whose PK repeats), mirroring MetricsService.data_quality;
    # no PK-bearing rows -> None.
    assert duplicate_rate_for_db(tmp_path, "p2") is None


def test_duplicate_rate_none_for_missing_db(tmp_path):
    assert duplicate_rate_for_db(tmp_path, "nope") is None


def test_duplicate_rate_skips_sqlite_sequence(tmp_path):
    db = _mkdb(tmp_path, "p3")
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, v TEXT)")
    con.execute("INSERT INTO t (v) VALUES ('a'),('b')")
    con.commit()
    con.close()
    assert duplicate_rate_for_db(tmp_path, "p3") == 0.0