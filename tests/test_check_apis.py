import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_apis", ROOT / "scripts/check_apis.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.api = monitor.load_config(ROOT / "monitor/apis.json")["apis"][0]

    def test_validation(self):
        self.assertTrue(monitor.matches({"location": {"city": "杭州"}}, {"location.city": "杭州"}))
        for payload in ({}, {"found": False}, {"found": 1}, []):
            self.assertFalse(monitor.matches(payload, {"found": True}))

    def test_baidu_array_validation(self):
        api = next(item for item in monitor.load_config(ROOT / "monitor/apis.json")["apis"] if item["id"] == "baidu-ip-lookup")
        payload = {"status": "0", "data": [{"origip": "110.96.1.1", "resourceid": "6006"}]}
        self.assertTrue(monitor.matches(payload, api["expect"]))
        for invalid in ({"status": "0", "data": []}, {"status": "0"}, {"status": 0, "data": payload["data"]}, {"status": "0", "data": [{"origip": "1.1.1.1", "resourceid": "6006"}]}):
            self.assertFalse(monitor.matches(invalid, api["expect"]))
        for path in ("data.1.origip", "data.-1.origip", "data.x.origip"):
            self.assertFalse(monitor.matches(payload, {path: "110.96.1.1"}))

    def test_available_excludes_warmup(self):
        with patch.object(monitor, "probe", side_effect=[(9999, None)] + [(10, None), (20, None), (30, None), (40, None), (50, None)]):
            result = monitor.measure(self.api, interval=0)
        self.assertEqual(result["average_ms"], 30)
        self.assertEqual(result["status"], "available")

    def test_local_api_validation(self):
        apis = {item["id"]: item for item in monitor.load_config(ROOT / "monitor/apis.json")["apis"]}
        for ip in ("192.0.2.1", "198.51.100.2", "2001:db8::1"):
            payloads = {
                "qq-ip2city": {"ret": 0, "ip": ip, "isp": ""},
                "letv-ip": {"host": ip, "remote": ip, "desc": "Example location"},
                "ipip-myip": {"ret": "ok", "data": {"ip": ip, "location": ["Country", "", "City"]}},
            }
            for name, payload in payloads.items():
                with self.subTest(name=name, ip=ip):
                    self.assertTrue(monitor.valid_response(payload, apis[name]))
                    response = MagicMock()
                    response.status = 200
                    response.read.return_value = json.dumps(payload).encode()
                    response.__enter__.return_value = response
                    with patch.object(monitor, "urlopen", return_value=response):
                        self.assertIsNone(monitor.probe(apis[name], 1)[1])
        invalid = {
            "qq-ip2city": [{"ret": "0", "ip": "192.0.2.1"}, {"ret": 0}, {"ret": 0, "ip": "not-an-ip"}, {"ret": 0, "ip": 123}],
            "letv-ip": [{"host": "192.0.2.1", "remote": "192.0.2.1", "desc": " "}, {"host": "192.0.2.1", "desc": "Country"}],
            "ipip-myip": [{"ret": "ok", "data": {"ip": "192.0.2.1", "location": location}} for location in ([], ["", " "], [1], "Country")],
        }
        for name, payloads in invalid.items():
            for payload in payloads + [{}, None, []]:
                with self.subTest(name=name, payload=payload):
                    self.assertFalse(monitor.valid_response(payload, apis[name]))

    def test_validation_config_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apis.json"
            for rules in ({}, {"validate": {"ip": "typo"}}, {"expect": []}):
                api = {key: value for key, value in self.api.items() if key != "expect"}
                api.update(rules)
                path.write_text(json.dumps({"apis": [api]}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    monitor.load_config(path)

    def test_partial_failure(self):
        with patch.object(monitor, "probe", side_effect=[(None, "warmup"), (10, None), (None, "timeout"), (20, None), (None, "invalid"), (30, None)]):
            result = monitor.measure(self.api, interval=0)
        self.assertEqual((result["status"], result["success"], result["average_ms"]), ("unstable", 3, 20))

    def test_all_failed(self):
        with patch.object(monitor, "probe", return_value=(None, "timeout")):
            result = monitor.measure(self.api, interval=0)
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["average_ms"])

    def test_network_failure(self):
        with patch.object(monitor, "urlopen", side_effect=URLError("offline")):
            elapsed, error = monitor.probe(self.api, 1)
        self.assertIsNone(elapsed)
        self.assertIn("offline", error)

    def test_http_payloads(self):
        for status, raw, valid in [(200, b'{"found": true, "target": "110.96.1.1", "feature": "ip"}', True), (200, b'not json', False), (200, b'{"found":false}', False), (503, b'{}', False)]:
            with self.subTest(status=status, raw=raw):
                response = MagicMock()
                response.status = status
                response.read.return_value = raw
                response.__enter__.return_value = response
                with patch.object(monitor, "urlopen", return_value=response):
                    elapsed, error = monitor.probe(self.api, 1)
                self.assertEqual(error is None, valid)

    def test_preserves_manual_content(self):
        text = "intro\n" + monitor.START + "\nold\n" + monitor.END + "\nfooter"
        updated = monitor.update_readme(text, "new")
        self.assertEqual(updated, "intro\n" + monitor.START + "\n\nnew\n\n" + monitor.END + "\nfooter")
        self.assertEqual(monitor.update_readme(updated, "new"), updated)
        for invalid in ("no markers", monitor.END + monitor.START, text + monitor.START):
            with self.assertRaises(ValueError):
                monitor.update_readme(invalid, "new")

    def test_render_hides_query_without_changing_request(self):
        url = "https://example.com/api.php?query=110.96.1.1&format=1#section"
        api = dict(self.api, url=url)
        report = {"checked_at": "pending", "environment": "test", "results": []}
        text = monitor.render([api], report)
        self.assertIn("`https://example.com/api.php`", text)
        self.assertNotIn("?query=", text)
        self.assertNotIn("#section", text)
        self.assertEqual(api["url"], url)

    def test_render_multiple_apis_and_categories(self):
        apis = [self.api, dict(self.api, id="second", name="Second", category="local")]
        report = {"checked_at": "pending", "environment": "test", "results": []}
        text = monitor.render(apis, report)
        self.assertIn("**宝塔**", text)
        self.assertIn("**Second**", text)
        self.assertNotIn("请求方式", text)
        self.assertNotIn("返回信息", text)
        for line in text.splitlines():
            if line.startswith("|"):
                self.assertEqual(line.count("|"), 7)
        self.assertEqual(text.count("暂无收录。"), 1)
        self.assertEqual(text.count("⏳ 待检测"), 2)

    def test_static_catalog_has_no_measurements(self):
        text = monitor.render_catalog([self.api], "owner/repo")
        self.assertIn("https://github.com/owner/repo/tree/monitor-results", text)
        self.assertIn("| 接口 | URL | 文档 |", text)
        self.assertNotIn("最后检测", text)
        self.assertNotIn("待检测", text)

    def test_probe_does_not_modify_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "monitor").mkdir()
            (root / "monitor/apis.json").write_text(json.dumps({"apis": [self.api]}), encoding="utf-8")
            readme = root / "README.md"
            readme.write_text("manual source content", encoding="utf-8")
            before = (root / "monitor/apis.json").read_bytes()
            result = {"id": self.api["id"], "status": "available", "success": 5, "samples": 5, "average_ms": 10, "errors": []}
            with patch.object(monitor, "measure", return_value=result):
                monitor.main(["--root", str(root), "--repository", "owner/repo", "--source-ref", "abc123"])
            self.assertEqual(readme.read_text(encoding="utf-8"), "manual source content")
            self.assertEqual((root / "monitor/apis.json").read_bytes(), before)
            self.assertFalse((root / "monitor/latest.json").exists())
            output = root / "monitor/output"
            self.assertEqual(json.loads((output / "latest.json").read_text(encoding="utf-8"))["results"], [result])
            self.assertIn("https://github.com/owner/repo/blob/abc123/docs/", (output / "README.md").read_text(encoding="utf-8"))

    def test_initialize_writes_output_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "monitor").mkdir()
            (root / "monitor/apis.json").write_text(json.dumps({"apis": [self.api]}), encoding="utf-8")
            with patch.object(monitor, "measure") as measure:
                monitor.main(["--root", str(root), "--initialize"])
                measure.assert_not_called()
            self.assertFalse((root / "README.md").exists())
            self.assertTrue((root / "monitor/output/README.md").is_file())


if __name__ == "__main__":
    unittest.main()
