"""Probe APIs into an isolated output directory; source files stay unchanged."""

import argparse
import ipaddress
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

START = "<!-- ip-monitor:start -->"
END = "<!-- ip-monitor:end -->"
CATEGORIES = {
    "both": "🌐 本机 IP / 指定 IP 均支持",
    "local": "📍 仅支持本机 IP",
    "target": "🎯 仅支持指定 IP",
}
MISSING = object()
VALIDATORS = {"ip", "nonempty_string", "string_list"}


def load_config(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    ids = set()
    for api in config["apis"]:
        for key in ("id", "name", "category", "url", "method", "info", "doc"):
            if not api.get(key):
                raise ValueError(f"Missing API setting: {key}")
        if api["id"] in ids or api["category"] not in CATEGORIES:
            raise ValueError("Duplicate API ID or unknown category")
        if not api["url"].startswith("https://"):
            raise ValueError("API URL must use HTTPS")
        expected, validators = api.get("expect", {}), api.get("validate", {})
        if not isinstance(expected, dict) or not isinstance(validators, dict) or not (expected or validators):
            raise ValueError("At least one expect or validate rule is required")
        if any(rule not in VALIDATORS for rule in validators.values()):
            raise ValueError("Unknown field validator")
        ids.add(api["id"])
    if not config["apis"]:
        raise ValueError("No APIs configured")
    return config


def field(payload, path):
    actual = payload
    for part in path.split("."):
        if isinstance(actual, dict) and part in actual:
            actual = actual[part]
        elif isinstance(actual, list) and part.isascii() and part.isdecimal() and int(part) < len(actual):
            actual = actual[int(part)]
        else:
            return MISSING
    return actual


def matches(payload, expected):
    for path, value in expected.items():
        actual = field(payload, path)
        if type(actual) is not type(value) or actual != value:
            return False
    return True


def valid_response(payload, api):
    if not matches(payload, api.get("expect", {})):
        return False
    for path, rule in api.get("validate", {}).items():
        value = field(payload, path)
        if rule == "ip":
            if not isinstance(value, str):
                return False
            try:
                ipaddress.ip_address(value)
            except ValueError:
                return False
        elif rule == "nonempty_string":
            if not isinstance(value, str) or not value.strip():
                return False
        elif rule == "string_list":
            if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value) or not any(item.strip() for item in value):
                return False
        else:
            return False
    return True


def probe(api, timeout):
    body = api.get("body")
    headers = {"User-Agent": "ip-info-api-monitor/1.0", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    headers.update(api.get("headers", {}))
    request = Request(api["url"], data=None if body is None else json.dumps(body).encode(),
                      headers=headers, method=api["method"])
    start = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1_048_577)
            elapsed = (time.perf_counter() - start) * 1000
            if not 200 <= response.status < 300:
                return None, f"HTTP {response.status}"
            if len(raw) > 1_048_576:
                return None, "Response exceeds 1 MiB"
        if not valid_response(json.loads(raw), api):
            return None, "Response validation failed"
        return elapsed, None
    except HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def measure(api, samples=5, timeout=10, interval=1):
    probe(api, timeout)  # Warm-up is intentionally excluded from the average.
    durations, errors = [], []
    for _ in range(samples):
        time.sleep(interval)
        elapsed, error = probe(api, timeout)
        if error is None:
            durations.append(elapsed)
        else:
            errors.append(error)
    success = len(durations)
    return {
        "id": api["id"],
        "status": "available" if success == samples else "unstable" if success else "unavailable",
        "success": success,
        "samples": samples,
        "average_ms": round(sum(durations) / success, 2) if success else None,
        "errors": errors,
    }


def cell(value):
    return str(value).replace("|", "&#124;").replace("\n", " ").replace("\r", "")


def render(apis, report):
    results = {item["id"]: item for item in report["results"]}
    lines = [f"最后检测：{report['checked_at']}（北京时间） · 测试环境：{cell(report['environment'])}", ""]
    labels = {"available": "✅ 可用", "unstable": "⚠️ 不稳定", "unavailable": "❌ 不可用"}
    for category, title in CATEGORIES.items():
        lines.extend([f"### {title}", ""])
        entries = [api for api in apis if api["category"] == category]
        if not entries:
            lines.extend(["暂无收录。", ""])
            continue
        lines.extend([
            "| 接口 | URL | 可用状态 | 平均响应 | 成功次数 | 文档 |",
            "| :--- | :--- | :---: | ---: | :---: | :--- |",
        ])
        for api in entries:
            result = results.get(api["id"])
            status, average, count = "⏳ 待检测", "—", "—"
            if result:
                status = labels[result["status"]]
                average = "—" if result["average_ms"] is None else f"{result['average_ms']:.2f} ms"
                count = f"{result['success']}/{result['samples']}"
            display_url = urlsplit(api["url"])._replace(query="", fragment="").geturl()
            values = [f"**{api['name']}**", f"`{display_url}`",
                      status, average, count, f"[查看详情 →]({api['doc']})"]
            lines.append("| " + " | ".join(cell(value) for value in values) + " |")
        lines.append("")
    return "\n".join(lines).rstrip()


def update_readme(text, content):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one monitor marker pair")
    before, rest = text.split(START)
    _, after = rest.split(END)
    return before + START + "\n\n" + content + "\n\n" + END + after


def render_catalog(apis, repository):
    results_url = f"https://github.com/{repository}/tree/monitor-results"
    lines = [f"[查看最新检测结果：可用状态 / 平均响应 / 成功次数]({results_url})", "",
             "> 每 4 小时更新。结果存放于独立分支，首页不保存易过期的检测数值。首次发布前可在 Actions 中查看运行情况。", ""]
    for category, title in CATEGORIES.items():
        lines.extend([f"### {title}", ""])
        entries = [api for api in apis if api["category"] == category]
        if not entries:
            lines.extend(["暂无收录。", ""])
            continue
        lines.extend(["| 接口 | URL | 文档 |", "| :--- | :--- | :--- |"])
        for api in entries:
            url = urlsplit(api["url"])._replace(query="", fragment="").geturl()
            values = [f"**{api['name']}**", f"`{url}`", f"[查看详情 →]({api['doc']})"]
            lines.append("| " + " | ".join(cell(value) for value in values) + " |")
        lines.append("")
    return "\n".join(lines).rstrip()


def write_report(apis, report, output_dir, repository, source_ref):
    source_url = f"https://github.com/{repository}/tree/{quote(source_ref, safe='')}"
    docs_base = f"https://github.com/{repository}/blob/{quote(source_ref, safe='')}/"
    linked_apis = [dict(api, doc=docs_base + quote(api["doc"], safe="/")) for api in apis]
    markdown = "# IP 接口检测结果\n\n"
    markdown += f"[返回项目首页](https://github.com/{repository}) · [检测配置版本]({source_url})\n\n"
    markdown += "> 此分支仅存放自动生成的结果，请勿合并回代码分支。每 4 小时计划检测一次，可能延迟；请检查下方检测时间，不要将旧结果当作实时状态。\n\n"
    markdown += render(linked_apis, report) + "\n\n"
    markdown += "平均响应仅统计本轮成功样本；预热不计入。全部失败显示不可用，不代表所有网络环境均不可访问。\n\n[原始结果与失败原因](latest.json)\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "README.md").write_text(markdown, encoding="utf-8")
    (output_dir / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, help="Default: monitor/output (ignored by Git)")
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", "liuheo/ip-info-api"))
    parser.add_argument("--source-ref", default="master", help="Source commit or branch used for document links")
    parser.add_argument("--catalog-only", action="store_true", help="Explicitly refresh the static source README, without probing")
    parser.add_argument("--initialize", action="store_true", help="Render pending state without network requests")
    args = parser.parse_args(argv)
    config = load_config(args.root / "monitor/apis.json")
    if args.catalog_only:
        readme = args.root / "README.md"
        original = readme.read_text(encoding="utf-8")
        readme.write_text(update_readme(original, render_catalog(config["apis"], args.repository)), encoding="utf-8")
        return
    output_dir = args.output_dir or args.root / "monitor/output"
    if output_dir.resolve() in (args.root.resolve(), (args.root / "monitor").resolve()):
        parser.error("Output directory must not overwrite source README or monitor files")
    report = {
        "checked_at": "尚未执行",
        "environment": "GitHub Actions / ubuntu-latest",
        "results": [],
        "source_ref": args.source_ref,
        "repository": args.repository,
    }
    if not args.initialize:
        report["environment"] = "GitHub Actions / ubuntu-latest" if os.getenv("GITHUB_ACTIONS") == "true" else "本地运行（非 GitHub Actions）"
        report["results"] = [measure(api) for api in config["apis"]]
        report["checked_at"] = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    write_report(config["apis"], report, output_dir, args.repository, args.source_ref)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
