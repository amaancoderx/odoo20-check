"""Scan Odoo modules for Odoo 20 incompatibilities."""
from __future__ import annotations
import csv, io, re, pathlib
import xml.etree.ElementTree as ET
from .rules import BY_ID

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".idea", ".venv", "static",
             "upgrades", "migrations"}  # upgrade scripts reference old models on purpose

# Model references. Require a quote+model+quote so prose and comments do not match.
RE_IR_MODEL_ACCESS = re.compile(r"""['"]ir\.model\.access['"]""")
RE_IR_RULE = re.compile(r"""['"]ir\.rule['"]""")
RE_XML_MODEL_MA = re.compile(r"""model\s*=\s*["']ir\.model\.access["']""")
RE_XML_MODEL_RULE = re.compile(r"""model\s*=\s*["']ir\.rule["']""")
RE_GROUPS_FIELD = re.compile(r"\.(model_access|rule_groups)\b")
RE_RULES_COUNT = re.compile(r"\.rules_count\b")
RE_TREE = re.compile(r"<\s*tree\b")
RE_VERSION = re.compile(r"""["']version["']\s*:\s*["']([^"']+)["']""")
RE_OLD_SERIES = re.compile(r"^(?:[89]|1[0-9])\.0(?:\.|$)")  # 8.0 .. 19.0

OLD_PERM_COLS = {"perm_read", "perm_write", "perm_create", "perm_unlink"}


class Finding:
    __slots__ = ("rule_id", "file", "line", "snippet")

    def __init__(self, rule_id, file, line, snippet=""):
        self.rule_id, self.file, self.line = rule_id, str(file), line
        self.snippet = (snippet or "").strip()[:140]

    @property
    def rule(self):
        return BY_ID[self.rule_id]

    def as_dict(self):
        r = self.rule
        return {"rule": self.rule_id, "severity": r["severity"], "title": r["title"],
                "file": self.file, "line": self.line, "snippet": self.snippet,
                "fix": r["fix"], "evidence": r["evidence"]}


def _lines(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def _strip_py_comments(line):
    """Drop a trailing # comment so prose does not trigger model matches."""
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def scan_python(path, rel):
    found = []
    for n, raw in enumerate(_lines(path), 1):
        line = _strip_py_comments(raw)
        if RE_IR_MODEL_ACCESS.search(line):
            found.append(Finding("SEC003", rel, n, raw))
        if RE_IR_RULE.search(line):
            found.append(Finding("SEC004", rel, n, raw))
        if RE_GROUPS_FIELD.search(line):
            found.append(Finding("SEC005", rel, n, raw))
        if RE_RULES_COUNT.search(line):
            found.append(Finding("SEC006", rel, n, raw))
    return found


def scan_xml(path, rel):
    found, lines = [], _lines(path)
    for n, raw in enumerate(lines, 1):
        if RE_XML_MODEL_MA.search(raw):
            found.append(Finding("SEC003", rel, n, raw))
        if RE_XML_MODEL_RULE.search(raw):
            found.append(Finding("SEC004", rel, n, raw))
        if RE_TREE.search(raw):
            found.append(Finding("VIEW002", rel, n, raw))

    # search-view <group> attributes: structural, so parse rather than regex
    try:
        root = ET.parse(str(path)).getroot()
    except Exception:
        return found
    for search in root.iter("search"):
        for grp in search.iter("group"):
            bad = [a for a in ("expand", "string") if a in grp.attrib]
            if bad:
                snippet = f"<group {' '.join(f'{a}=\"{grp.attrib[a]}\"' for a in bad)}>"
                found.append(Finding("VIEW001", rel, _find_line(lines, bad[0], "group"), snippet))
    return found


def _find_line(lines, attr, tag):
    for i, l in enumerate(lines, 1):
        if f"<{tag}" in l and attr + "=" in l:
            return i
    return 0


def scan_security_csv(path, rel):
    found = [Finding("SEC001", rel, 0, path.name)]
    try:
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8", errors="ignore"))))
    except Exception:
        return found
    if rows:
        header = {h.strip() for h in rows[0]}
        if header & OLD_PERM_COLS:
            found.append(Finding("SEC002", rel, 1, ",".join(rows[0])))
    return found


def scan_manifest(path, rel):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    m = RE_VERSION.search(text)
    if not m:
        return []
    ver = m.group(1)
    # A bare version such as "1.1" is valid and series-agnostic; only an explicit
    # older series prefix (e.g. "17.0.1.0.0") needs bumping.
    if RE_OLD_SERIES.match(ver):
        line = text[: m.start()].count("\n") + 1
        return [Finding("MAN001", rel, line, m.group(0))]
    return []


def scan_module(module_dir) -> list:
    """Scan one Odoo module directory."""
    module_dir = pathlib.Path(module_dir)
    found = []
    for path in sorted(module_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(module_dir.parent)
        if path.name == "ir.model.access.csv" and path.parent.name == "security":
            found += scan_security_csv(path, rel)
        elif path.name == "__manifest__.py":
            found += scan_manifest(path, rel)
        elif path.suffix == ".py":
            found += scan_python(path, rel)
        elif path.suffix == ".xml":
            found += scan_xml(path, rel)
    return found


def is_module(path) -> bool:
    return (pathlib.Path(path) / "__manifest__.py").is_file()


def find_modules(root):
    root = pathlib.Path(root)
    if is_module(root):
        return [root]
    out = []
    for p in sorted(root.iterdir()) if root.is_dir() else []:
        if p.is_dir() and p.name not in SKIP_DIRS and is_module(p):
            out.append(p)
    return out
