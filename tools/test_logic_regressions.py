import base64
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import yaml
from flask import Flask
from admin.app import save_yaml
from admin import sync, github_write

class LogicRegressionTests(unittest.TestCase):
    def test_yaml_preserves_package_values(self):
        package = {"identifier": "test", "name": "Test", "screenshots": ["assets/custom.png"],
                   "supportedOS": [{"minimum": "26.0", "maximum": "26.1", "builds": ["custom"]}]}
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "repo.yml"
            save_yaml(target, {"packages": [package]}, packages_meta=[{"use_anchor_screens": True, "use_anchor_os": True}])
            actual = yaml.safe_load(target.read_text(encoding="utf-8"))["packages"][0]
            self.assertEqual(actual["screenshots"], package["screenshots"])
            self.assertEqual(actual["supportedOS"], package["supportedOS"])

    def test_binary_encoded_once_and_branch_preserved(self):
        raw = b"\x89PNG\r\n\xff"
        response = Mock(status_code=201)
        response.json.return_value = {"commit": {"sha": "new"}}
        with patch.object(github_write, "_get_repo_metadata", return_value={"default_branch": "main"}), patch.object(github_write, "_get_file_sha", return_value=None), patch.object(github_write.requests, "put", return_value=response) as put:
            github_write.write_binary_file("token", "owner/repo", "test.png", raw, "test", branch="sync-branch")
            payload = put.call_args.kwargs["json"]
            self.assertEqual(base64.b64decode(payload["content"]), raw)
            self.assertEqual(payload["branch"], "sync-branch")

    def test_collect_refreshes_defaults_and_includes_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for name, data in [(".3105/admin-settings.json", b'{"theme":"pink"}'), ("repositories/demo/packages/test.3105", b"package"), ("repositories/demo/assets/test.png", b"image")]:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            paths = {f["path"] for f in sync.collect_local_files(root)}
            self.assertIn("repositories/demo/packages/test.3105", paths)
            self.assertIn("repositories/demo/assets/test.png", paths)
            self.assertEqual(json.loads((root / ".3105/public-defaults.json").read_text())["theme"], "pink")

    def test_clean_push_does_not_commit(self):
        from admin.app import app
        import subprocess
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch("subprocess.run", side_effect=run):
            result = app.test_client().post("/api/repo/demo/push", json={}).get_json()
        self.assertEqual(result["step"], "nothing-to-commit")
        self.assertIn(("git", "status", "--porcelain"), calls)
        self.assertFalse(any("commit" in command for command in calls))

    def test_deleted_only_sync_calls_delete(self):
        app = Flask(__name__)
        app.secret_key = "test"
        config = type("Config", (), {"GITHUB_PAT": "test", "GITHUB_API_BASE": "https://example.invalid"})
        with tempfile.TemporaryDirectory() as directory:
            sync.register_sync_routes(app, pathlib.Path(directory), config)
            remote = [{"path": "assets/blog/old.png", "sha": "old", "size": 1}]
            response = Mock()
            response.json.return_value = {"sha": "full-sha"}
            with patch.object(sync, "collect_local_files", return_value=[]), patch.object(sync, "fetch_remote_files", return_value=remote), patch.object(github_write, "_get_repo_metadata", return_value={"default_branch": "main"}), patch.object(sync.requests, "get", return_value=response), patch.object(sync.requests, "delete", return_value=response) as delete:
                result = app.test_client().post("/api/sync/push", json={}).get_json()
                self.assertTrue(result["ok"])
                self.assertEqual(result["deleted"], 1)
                self.assertEqual(delete.call_args.kwargs["json"]["sha"], "full-sha")

if __name__ == "__main__":
    unittest.main()
