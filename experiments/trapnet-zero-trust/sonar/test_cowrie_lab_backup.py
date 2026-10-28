import tempfile
from pathlib import Path
import unittest
import cowrie_lab_backup as audit

class PrivateVarBackupTests(unittest.TestCase):
    def fixture(self,root):
        directory=Path(root)/"log/cowrie";directory.mkdir(parents=True)
        (directory/"cowrie.json").write_text('{"eventid":"cowrie.session.connect"}\n')
        (Path(root)/"run").mkdir()
        (Path(root)/"lib/cowrie").mkdir(parents=True)
    def test_copy_restore_and_digest(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)
            source=base/"var";self.fixture(source)
            proof=audit.copy_verified(source,base/"offline-backup")
            (source/"log/cowrie/cowrie.json").unlink()
            with self.assertRaises(ValueError):
                audit.copy_verified(source,base/"invalid-copy",proof)
            copy=audit.copy_verified(base/"offline-backup",base/"restored",proof)
            self.assertEqual(copy,proof)
    def test_corrupted_backup_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)
            source=base/"var";self.fixture(source)
            proof=audit.copy_verified(source,base/"offline-backup")
            (base/"offline-backup/log/cowrie/cowrie.json").write_text("TRUNCATED")
            with self.assertRaises(ValueError):
                audit.copy_verified(base/"offline-backup",base/"restored",proof)
            self.assertFalse((base/"restored").exists())
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);source=base/"var";self.fixture(source)
            with self.assertRaises(ValueError):
                audit.copy_verified(source,source)
    def test_size_guard(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);source=base/"var";self.fixture(source)
            with (source/"log/cowrie/cowrie.json").open("ab") as f:
                f.write(b"x"*(audit.MAX_BYTES+1))
            with self.assertRaises(ValueError):audit.manifest(source)
    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);source=base/"var";self.fixture(source)
            try:(source/"log/cowrie/alias").symlink_to(source/"log/cowrie/cowrie.json")
            except OSError:self.skipTest("symlink privilege unavailable")
            with self.assertRaises(ValueError):audit.manifest(source)
    def test_hardlink_refused(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);source=base/"var";self.fixture(source)
            try:os_link=__import__("os").link;os_link(source/"log/cowrie/cowrie.json",source/"log/cowrie/copy")
            except OSError:self.skipTest("hardlinks unavailable")
            with self.assertRaises(ValueError):audit.manifest(source)

if __name__=="__main__":unittest.main()
