import tempfile
import unittest
from pathlib import Path
import automation

class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = automation.DB_PATH
        automation.DB_PATH = Path(self.tmp.name) / "test.sqlite3"

    def tearDown(self):
        automation.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_db_initialises_profile_and_policy_disabled(self):
        c = automation.db()
        profile = c.execute("SELECT * FROM profile WHERE id=1").fetchone()
        cfg = c.execute("SELECT * FROM automation_settings WHERE id=1").fetchone()
        self.assertIsNotNone(profile)
        self.assertEqual(cfg["enabled"], 0)
        c.close()

    def test_disabled_run_does_not_search_or_send(self):
        automation.run_once()
        c = automation.db()
        events = [r[0] for r in c.execute("SELECT event FROM activity").fetchall()]
        self.assertIn("autopilot_idle", events)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM applications").fetchone()[0], 0)
        c.close()

    def test_scoring_returns_bounded_integer(self):
        value = automation.score({"title":"Operations Executive", "description":"procurement logistics inventory"}, "operations procurement", "logistics inventory")
        self.assertIsInstance(value, int)
        self.assertGreaterEqual(value, 0)
        self.assertLessEqual(value, 100)

if __name__ == "__main__":
    unittest.main()
