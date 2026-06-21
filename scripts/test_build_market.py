import json
import tempfile
import unittest
from pathlib import Path

import build_market


class BuildMarketTests(unittest.TestCase):
    def test_builds_registry_and_zip_with_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "codex-review"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: codex-review\n"
                "description: Review code changes with Codex.\n"
                "license: MIT\n"
                "---\n\n"
                "# Codex Review\n",
                encoding="utf-8",
            )
            market_dir = root / "market"
            market_dir.mkdir()
            (market_dir / "categories.json").write_text(
                json.dumps(
                    {
                        "categories": [
                            {"id": "engineering", "name": "Engineering", "description": "Build and review code"}
                        ],
                        "skills": {
                            "codex-review": {
                                "category": "engineering",
                                "tags": ["codex", "review"],
                                "runtime": ["codex", "claude", "portable"],
                                "riskLevel": "low",
                                "source": "local-test",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            registry = build_market.build_market(root, write=True)
            item = registry["skills"][0]

            self.assertEqual(registry["schemaVersion"], "1.0")
            self.assertEqual(item["id"], "codex-review")
            self.assertEqual(item["category"], "engineering")
            self.assertEqual(item["installTargets"]["codex"], "~/.codex/skills/codex-review")
            self.assertEqual(item["installTargets"]["claude"], "~/.claude/skills/codex-review")
            self.assertTrue(item["archive"]["sha256"])
            self.assertTrue((root / item["archive"]["path"]).exists())
            self.assertTrue((root / "market" / "index.json").exists())

    def test_rejects_duplicate_skill_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("a", "b"):
                skill_dir = root / "skills" / folder
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    "---\nname: same-name\ndescription: duplicate\n---\n\n# Duplicate\n",
                    encoding="utf-8",
                )
            (root / "market").mkdir()
            (root / "market" / "categories.json").write_text(
                json.dumps({"categories": [], "skills": {}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(build_market.MarketError, "Duplicate skill name"):
                build_market.build_market(root, write=False)

    def test_rejects_secret_like_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "leaky"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: leaky\ndescription: bad\n---\n\nsk-1234567890abcdef\n",
                encoding="utf-8",
            )
            (root / "market").mkdir()
            (root / "market" / "categories.json").write_text(
                json.dumps({"categories": [], "skills": {}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(build_market.MarketError, "secret-like"):
                build_market.build_market(root, write=False)

    def test_rejects_stale_archive_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "codex-review"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                "---\n"
                "name: codex-review\n"
                "description: Review code changes with Codex.\n"
                "---\n\n"
                "# Codex Review\n",
                encoding="utf-8",
            )
            market_dir = root / "market"
            market_dir.mkdir()
            (market_dir / "categories.json").write_text(
                json.dumps({"categories": [], "skills": {}}),
                encoding="utf-8",
            )

            build_market.build_market(root, write=True)
            build_market.validate_existing_artifacts(root)

            skill_md.write_text(
                "---\n"
                "name: codex-review\n"
                "description: Review code changes with Codex.\n"
                "---\n\n"
                "# Changed\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(build_market.MarketError, "archive file is stale"):
                build_market.validate_existing_artifacts(root)


if __name__ == "__main__":
    unittest.main()
