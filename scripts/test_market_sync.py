import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import market_sync


def skill(skill_id, version="1.0.0", sha="abc", risk="low"):
    return {
        "id": skill_id,
        "name": skill_id,
        "description": "test",
        "category": "engineering",
        "tags": [],
        "runtime": ["portable"],
        "installTargets": {"portable": f"~/.agents/skills/{skill_id}"},
        "version": version,
        "license": "MIT",
        "source": "test",
        "riskLevel": risk,
        "path": f"skills/{skill_id}",
        "archive": {"path": f"dist/skills/{skill_id}.zip", "sha256": sha, "size": 1},
    }


def registry(*items):
    return {
        "schemaVersion": "1.0",
        "generatedAt": "2026-01-01T00:00:00Z",
        "repository": "local",
        "categories": [],
        "skills": list(items),
    }


class MarketSyncTests(unittest.TestCase):
    def test_diff_classifies_new_current_upgrade_and_risk_increase(self):
        local = registry(
            skill("current", "1.0.0", "same", "low"),
            skill("upgrade", "1.0.0", "old", "low"),
            skill("risk", "1.0.0", "old-risk", "low"),
        )
        remote = registry(
            skill("current", "1.0.0", "same", "low"),
            skill("upgrade", "1.1.0", "new", "low"),
            skill("risk", "1.0.1", "new-risk", "high"),
            skill("new-skill", "0.1.0", "new", "medium"),
        )

        result = {item["id"]: item for item in market_sync.diff_registries(local, remote)}

        self.assertEqual(result["current"]["status"], "current")
        self.assertEqual(result["upgrade"]["status"], "upgradable")
        self.assertEqual(result["risk"]["status"], "risk_increased")
        self.assertEqual(result["new-skill"]["status"], "new")

    def test_archive_verification_reports_checksum_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "dist" / "skills" / "broken.zip"
            archive.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("SKILL.md", "hello")
            remote = registry(skill("broken", "1.0.0", "not-the-real-sha", "low"))

            result = market_sync.diff_registries(registry(), remote, root=root, verify_archives=True)

            self.assertEqual(result[0]["status"], "checksum_failed")
            self.assertIn("sha256", result[0]["reason"])

    def test_summary_counts_statuses(self):
        result = [
            {"id": "a", "status": "new"},
            {"id": "b", "status": "new"},
            {"id": "c", "status": "current"},
        ]

        self.assertEqual(market_sync.summarize(result), {"new": 2, "current": 1})


if __name__ == "__main__":
    unittest.main()
