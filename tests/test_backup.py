import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "crm_backup", Path(__file__).parents[1] / "scripts/backup.py"
)
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db = self.root / "source.db"
        self.uploads = self.root / "uploads"
        self.uploads.mkdir()
        self.key = "a" * 32
        self.content = b"Real binary attachment\x00\xff"
        (self.uploads / self.key).write_bytes(self.content)
        with sqlite3.connect(self.db) as db:
            db.executescript("""CREATE TABLE orgs(id TEXT); CREATE TABLE users(id TEXT);
            CREATE TABLE crm_schema_migrations(version TEXT);
            CREATE TABLE attachments(storage_key TEXT, sha256 TEXT, size_bytes INTEGER);
            INSERT INTO orgs VALUES ('fixture-org');""")
            db.execute(
                "INSERT INTO attachments VALUES(?,?,?)",
                (self.key, hashlib.sha256(self.content).hexdigest(), len(self.content)),
            )
        self.snapshot = self.root / "snapshot"

    def test_round_trip_preserves_database_and_exact_attachment_bytes(self):
        backup.backup(self.db, self.uploads, self.snapshot)
        backup.verify(self.snapshot)
        restored = self.root / "restored"
        backup.restore(self.snapshot, restored)
        with sqlite3.connect(restored / "relay.db") as db:
            self.assertEqual(
                db.execute("SELECT id FROM orgs").fetchone()[0], "fixture-org"
            )
        self.assertEqual((restored / "uploads" / self.key).read_bytes(), self.content)
        self.assertEqual((restored / "relay.db").stat().st_mode & 0o777, 0o600)

    def test_refuses_overwrite(self):
        backup.backup(self.db, self.uploads, self.snapshot)
        with self.assertRaises(ValueError):
            backup.backup(self.db, self.uploads, self.snapshot)
        with self.assertRaises(ValueError):
            backup.restore(self.snapshot, self.root)

    def test_missing_attachment_leaves_no_partial_backup(self):
        (self.uploads / self.key).unlink()
        with self.assertRaises(ValueError):
            backup.backup(self.db, self.uploads, self.snapshot)
        self.assertFalse(self.snapshot.exists())

    def test_tampered_file_rejected_without_restore(self):
        backup.backup(self.db, self.uploads, self.snapshot)
        (self.snapshot / "uploads" / self.key).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            backup.restore(self.snapshot, self.root / "restored")
        self.assertFalse((self.root / "restored").exists())

    def test_missing_source_never_creates_database(self):
        missing = self.root / "missing.db"
        with self.assertRaises(ValueError):
            backup.backup(missing, self.uploads, self.snapshot)
        self.assertFalse(missing.exists())

    def test_tampered_database_rejected(self):
        backup.backup(self.db, self.uploads, self.snapshot)
        with sqlite3.connect(self.snapshot / "relay.db") as db:
            db.execute("DELETE FROM orgs")
        with self.assertRaises(ValueError):
            backup.verify(self.snapshot)

    def test_traversal_key_rejected_even_with_updated_database_digest(self):
        backup.backup(self.db, self.uploads, self.snapshot)
        with sqlite3.connect(self.snapshot / "relay.db") as db:
            db.execute("UPDATE attachments SET storage_key='../escape'")
        manifest = json.loads((self.snapshot / "manifest.json").read_text())
        manifest["database_sha256"] = backup.digest(self.snapshot / "relay.db")
        (self.snapshot / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            backup.verify(self.snapshot)


if __name__ == "__main__":
    unittest.main()
