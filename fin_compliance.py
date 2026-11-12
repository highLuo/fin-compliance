#!/usr/bin/env python3
"""fin-compliance - 金融内容合规标注扫描器（纯标准库，零依赖）。

扫描金融营销 / 投教 / 研报类文本，识别合规风险：
收益承诺、荐股暗示、夸大宣传、引流话术、AI 生成内容未标识。
支持 JSON / 表格输出、自定义规则、CI 友好退出码、内置 self-test。

用法：
  python fin_compliance.py <目录或文件> [--rules rules.json] [--format json|table]
  python fin_compliance.py --self-test
"""
import argparse
import fnmatch
import json
import os
import re
import sys

_DEFAULT_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
_MAX_FILE_BYTES = 2 * 1024 * 1024
_TEXT_EXTS = {".txt", ".md", ".markdown", ".rst", ".html", ".htm",
              ".json", ".csv", ".py", ".java", ".js", ".ts", ".go",
              ".yml", ".yaml"}


def _load_ignore(ignore_file):
    """读取 .fincomplianceignore（gitignore 风格）。"""
    patterns = []
    if not ignore_file or not os.path.exists(ignore_file):
        return patterns
    with open(ignore_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
    return patterns


def _is_ignored(rel_path, patterns):
    if not patterns:
        return False
    rel_norm = rel_path.replace("\\", "/")
    name = os.path.basename(rel_path)
    for p in patterns:
        pp = p.strip().replace("\\", "/")
        if not pp:
            continue
        if pp.endswith("/"):
            if rel_norm == pp.rstrip("/") or rel_norm.startswith(pp):
                return True
        if fnmatch.fnmatch(rel_norm, pp) or fnmatch.fnmatch(name, pp):
            return True
    return False


def load_rules(path: str):
    p = path or _DEFAULT_RULES_PATH
    if not os.path.exists(p):
        raise ValueError("规则文件不存在: %s" % p)
    with open(p, "r", encoding="utf-8") as f:
        rules = json.load(f)
    if not isinstance(rules, list):
        raise ValueError("规则文件必须是 JSON 数组")
    return rules


def _is_text(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
        return b"\x00" not in chunk
    except Exception:
        return False


def _scan_file(path: str, rules, base_dir: str) -> list:
    """扫描单个文件，返回命中列表。"""
    findings = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        content = "".join(lines)
    except Exception:
        return findings

    for rule in rules:
        rtype = rule.get("type", "regex")
        if rtype == "missing_marker":
            markers = rule.get("markers", [])
            if markers and not any(m in content for m in markers):
                findings.append({
                    "file": os.path.relpath(path, base_dir),
                    "line": 0,
                    "rule": rule.get("name", "missing_marker"),
                    "severity": rule.get("severity", "low"),
                    "category": rule.get("category", "AI标识"),
                    "snippet": rule.get("message", "全文未检测到 AI 生成内容标识"),
                })
            continue
        try:
            rx = re.compile(rule["pattern"])
        except re.error:
            continue
        for i, line in enumerate(lines, 1):
            m = rx.search(line)
            if m:
                findings.append({
                    "file": os.path.relpath(path, base_dir),
                    "line": i,
                    "rule": rule.get("name", "regex"),
                    "severity": rule.get("severity", "medium"),
                    "category": rule.get("category", "other"),
                    "snippet": line.strip()[:120],
                })
    return findings


def scan_directory(directory: str, rules, ignore=None) -> list:
    findings = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            fp = os.path.join(root, name)
            rel = os.path.relpath(fp, directory)
            if _is_ignored(rel, ignore):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in _TEXT_EXTS:
                continue
            if os.path.getsize(fp) > _MAX_FILE_BYTES or not _is_text(fp):
                continue
            findings.extend(_scan_file(fp, rules, directory))
    return findings


def _tally(findings):
    by = {}
    for f in findings:
        by[f["severity"]] = by.get(f["severity"], 0) + 1
    return by


def output_json(findings):
    print(json.dumps({"findings": findings, "count": len(findings),
                      "by_severity": _tally(findings)}, indent=2, ensure_ascii=False))


def output_table(findings):
    if not findings:
        print("未发现合规风险标注问题。")
        return
    print("%-30s %-5s %-7s %-12s %s" % ("FILE", "LINE", "SEV", "CATEGORY", "SNIPPET"))
    print("-" * 110)
    for f in findings:
        line = f.get("line") or 0
        print("%-30s %-5s %-7s %-12s %s" % (
            f["file"][:28], str(line), f["severity"], f["category"][:10], f["snippet"][:46]))


def run_self_test() -> bool:
    """内置自检：用临时样本验证检测能力。"""
    import tempfile
    # 样本触发器用拼接构造，避免源码本身被自家扫描器误报
    bait = (
        "推荐" + "买入" + "这只股票，必涨！" + "\n"
        "本产品" + "保本" + "保收益，无风险收益。" + "\n"
        "年化" + "15%" + "，稳赚不赔。" + "\n"
        "加" + "微信" + "一对一指导，老师带单。" + "\n"
        "正常使用的一段话，没有任何问题。" + "\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "sample.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(bait)
        rules = load_rules(None)
        found = _scan_file(p, rules, d)
    cats = {x["category"] for x in found}
    expected = {"收益承诺", "荐股", "引流", "AI标识"}
    passed = expected.issubset(cats)
    print("[self-test] 命中 %d 条，类别: %s" % (len(found), sorted(cats)))
    print("[self-test] " + ("PASS" if passed else "FAIL (未检出预期类别)"))
    return passed


def main(argv=None):
    parser = argparse.ArgumentParser(description="fin-compliance - 金融内容合规标注扫描器")
    parser.add_argument("directory", nargs="?", help="要扫描的目录或文件")
    parser.add_argument("--rules", default=None, help="自定义规则 JSON 路径（默认 rules.json）")
    parser.add_argument("--ignore-file", default=None, help="忽略清单（默认 <路径>/.fincomplianceignore）")
    parser.add_argument("--format", choices=["json", "table"], default="table", help="输出格式")
    parser.add_argument("--fail-on", choices=["high", "medium", "low", "none"], default="high",
                        help="达到该严重级别即返回非零退出码（none=只报告不失败）")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检并退出")
    args = parser.parse_args(argv)

    if args.self_test:
        return 0 if run_self_test() else 1

    if not args.directory:
        parser.error("必须提供 directory，或使用 --self-test")

    try:
        rules = load_rules(args.rules)
    except Exception as e:
        print("[错误] 加载规则失败: %s" % e, file=sys.stderr)
        return 2

    ignore_file = args.ignore_file or os.path.join(args.directory, ".fincomplianceignore")
    ignore = _load_ignore(ignore_file)

    if os.path.isfile(args.directory):
        findings = _scan_file(args.directory, rules,
                              os.path.dirname(os.path.abspath(args.directory)) or ".")
    else:
        findings = scan_directory(args.directory, rules, ignore=ignore)

    if args.format == "json":
        output_json(findings)
    else:
        output_table(findings)

    order = {"high": 3, "medium": 2, "low": 1, "none": 0}
    threshold = order.get(args.fail_on, 3)
    worst = max([order.get(f["severity"], 0) for f in findings], default=0)
    return 1 if worst >= threshold else 0


if __name__ == "__main__":
    sys.exit(main())
