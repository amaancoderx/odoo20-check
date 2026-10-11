# odoo20-check

Tells you what breaks when an Odoo module moves to **Odoo 20**, with file, line and fix.

Odoo's official upgrade service migrates your database and standard apps. It explicitly
does **not** upgrade the source of custom or third-party modules. That part is yours,
and Odoo 20 rewrote the security model, so it is not a small part.

```bash
pip install odoo20-check
odoo20-check /path/to/your/addons
```

```
hr_expense  14 blocker(s)
  BLOCKER SEC001  security/ir.model.access.csv must be renamed to ir.access.csv
      hr_expense/security/ir.model.access.csv
      fix: Rename to security/ir.access.csv, update __manifest__.py, convert columns.
  BLOCKER SEC004  model 'ir.rule' no longer exists
      hr_expense/security/ir_rule.xml:4
        <record id="ir_rule_hr_expense_manager" model="ir.rule">
      ... and 7 more
      fix: Record rules merged into 'ir.access'. Put the domain in the 'domain' field.

1/1 module(s) need changes for Odoo 20: 14 blockers, 0 warnings
```

`--json` for machine output, `--blockers-only` to hide warnings, `--quiet` for totals.
Exit code is 1 when blockers are found, so it drops into CI.

## How the rules were derived

Not from release notes. Every rule comes from diffing the Odoo 19.0 and 20.0 source
trees, and each one ships with the evidence that produced it:

| Rule | Finding | Evidence |
|---|---|---|
| SEC001 | `ir.model.access.csv` renamed to `ir.access.csv` | 19 core: 220 old / 0 new. 20 core: 0 old / 226 new |
| SEC002 | `perm_*` columns replaced by `operation` | 20 core header: `id,name,model_id/id,group_id/id,operation,domain` |
| SEC003 | model `ir.model.access` removed | `_name` defined once in 19 core, zero times in 20 |
| SEC004 | model `ir.rule` removed, merged into `ir.access` | same |
| SEC005 | `res.groups.model_access` / `.rule_groups` removed | field diff: added `access_ids`, `access_count` |
| SEC006 | `res.users.rules_count` removed | field diff |
| VIEW001 | search `<group>` rejects `expand` / `string` | RelaxNG validation error from Odoo 20 itself |
| VIEW002 | `<tree>` is not a valid element | zero `<tree` in 19 and 20 core views |
| MAN001 | manifest declares an older series | bare versions like `1.1` are valid; only an explicit old series is wrong |
| ENV001 | Odoo 20 needs PostgreSQL 16+ | base uses `any_value()`, added in PG16; PG15 fails at init |

## Measured accuracy

Most linters do not publish this. These numbers are reproducible with the commands below.

**Precision** — run against Odoo 20 core, which is by definition already v20-correct:

```
641 modules scanned · 0 blockers · 3 warnings
```

The 3 warnings are real stale version strings in Odoo's own core (`l10n_fi` declares
`13.0.2`), not false positives.

**Recall** — run against Odoo 19 core:

```
638 modules scanned · 226 flagged
SEC001  220   (ground truth: exactly 220 addons carry the old CSV)
SEC002  220
SEC004  590
SEC003   17
```

SEC001 found 220 of 220. Reproduce with:

```bash
odoo20-check /path/to/odoo-20/addons   # expect no blockers
odoo20-check /path/to/odoo-19/addons   # expect ~226 modules flagged
```

## What it does not do

- It does not rewrite your code. It reports, with the fix described.
- It does not migrate data. Use OCA OpenUpgrade for the database.
- It is static analysis, so a dynamically built model name is invisible to it.
- `upgrades/` and `migrations/` directories are skipped, because migration scripts
  reference removed models deliberately.

## Tests

```bash
python -m unittest discover -s tests
```

8 tests, including that a comment mentioning `ir.rule` does not trigger a finding and
that a clean v20 module produces no output.

## Licence

MIT.
