"""odoo20-check: report what breaks when an Odoo module moves to Odoo 20."""
from __future__ import annotations
import argparse, json, sys, collections, pathlib
from .rules import BY_ID
from .scanner import scan_module, find_modules

C = {"red": "\033[31m", "yellow": "\033[33m", "dim": "\033[2m",
     "bold": "\033[1m", "green": "\033[32m", "off": "\033[0m"}


def paint(s, c, enable):
    return f"{C[c]}{s}{C['off']}" if enable else s


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="odoo20-check",
        description="Report what breaks when an Odoo module moves to Odoo 20.")
    ap.add_argument("path", nargs="?", default=".",
                    help="a module directory, or a directory of modules")
    ap.add_argument("--json", action="store_true", help="machine readable output")
    ap.add_argument("--quiet", action="store_true", help="only show totals")
    ap.add_argument("--blockers-only", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args(argv)

    root = pathlib.Path(a.path).resolve()
    if not root.exists():
        print(f"no such path: {root}", file=sys.stderr)
        return 2
    modules = find_modules(root)
    if not modules:
        print(f"no Odoo modules found under {root} "
              f"(a module is a directory containing __manifest__.py)", file=sys.stderr)
        return 2

    color = sys.stdout.isatty() and not a.no_color
    results, counts = {}, collections.Counter()
    for m in modules:
        fs = scan_module(m)
        if a.blockers_only:
            fs = [f for f in fs if f.rule["severity"] == "blocker"]
        results[m.name] = fs
        for f in fs:
            counts[f.rule_id] += 1

    if a.json:
        print(json.dumps({
            "modules_scanned": len(modules),
            "modules_affected": sum(1 for v in results.values() if v),
            "findings": {k: [f.as_dict() for f in v] for k, v in results.items() if v},
            "rule_counts": dict(counts),
        }, indent=2))
    else:
        affected = {k: v for k, v in results.items() if v}
        if not a.quiet:
            for name, fs in affected.items():
                blockers = sum(1 for f in fs if f.rule["severity"] == "blocker")
                print(f"\n{paint(name, 'bold', color)}  "
                      f"{paint(str(blockers) + ' blocker(s)', 'red', color) if blockers else ''}"
                      f"{paint(f'  {len(fs) - blockers} warning(s)', 'yellow', color) if len(fs) - blockers else ''}")
                by_rule = collections.defaultdict(list)
                for f in fs:
                    by_rule[f.rule_id].append(f)
                for rid, items in sorted(by_rule.items()):
                    r = BY_ID[rid]
                    sev = paint("BLOCKER", "red", color) if r["severity"] == "blocker" \
                        else paint("warning", "yellow", color)
                    print(f"  {sev} {rid}  {r['title']}")
                    for f in items[:5]:
                        loc = f"{f.file}:{f.line}" if f.line else str(f.file)
                        print(f"      {paint(loc, 'dim', color)}")
                        if f.snippet:
                            print(f"        {paint(f.snippet, 'dim', color)}")
                    if len(items) > 5:
                        print(f"      {paint(f'... and {len(items) - 5} more', 'dim', color)}")
                    print(f"      {paint('fix: ' + r['fix'], 'dim', color)}")
        total_block = sum(1 for fs in results.values() for f in fs
                          if f.rule["severity"] == "blocker")
        total_warn = sum(len(fs) for fs in results.values()) - total_block
        print()
        if total_block or total_warn:
            print(f"{len(affected)}/{len(modules)} module(s) need changes for Odoo 20: "
                  f"{paint(str(total_block) + ' blockers', 'red', color)}, "
                  f"{paint(str(total_warn) + ' warnings', 'yellow', color)}")
        else:
            print(paint(f"{len(modules)} module(s) scanned, nothing found that blocks Odoo 20.",
                        "green", color))

    return 1 if any(f.rule["severity"] == "blocker"
                    for fs in results.values() for f in fs) else 0


if __name__ == "__main__":
    sys.exit(main())
