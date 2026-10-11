"""Odoo 20 breaking-change rules.

Every rule carries the evidence it was derived from. Rules were extracted by
diffing the Odoo 19.0 and 20.0 source trees, not from release notes.
"""

# severity: "blocker" = module will not install; "warn" = behaviour/API change
RULES = [
    dict(
        id="SEC001", severity="blocker",
        title="security/ir.model.access.csv must be renamed to ir.access.csv",
        evidence="odoo 19 core: 220 ir.model.access.csv, 0 ir.access.csv. "
                 "odoo 20 core: 0 ir.model.access.csv, 226 ir.access.csv.",
        fix="Rename the file to security/ir.access.csv, update __manifest__.py "
            "data, and convert columns (see SEC002).",
    ),
    dict(
        id="SEC002", severity="blocker",
        title="access CSV columns changed: perm_* replaced by operation",
        evidence="odoo 20 core ir.access.csv header is "
                 "id,name,model_id/id,group_id/id,operation,domain",
        fix="Replace perm_read/perm_write/perm_create/perm_unlink with a single "
            "'operation' column holding CRUD letters (r, cr, crud, ...). "
            "'u' means write/update, 'd' means unlink/delete. Add an optional "
            "'domain' column. model_id:id becomes model_id/id.",
    ),
    dict(
        id="SEC003", severity="blocker",
        title="model 'ir.model.access' no longer exists",
        evidence="_name = 'ir.model.access' defined once in odoo 19 core, "
                 "zero times in odoo 20.",
        fix="Use 'ir.access'. A record with a group_id is a permission; "
            "without one it is a restriction applying to everybody.",
    ),
    dict(
        id="SEC004", severity="blocker",
        title="model 'ir.rule' no longer exists",
        evidence="_name = 'ir.rule' defined once in odoo 19 core, zero times in odoo 20.",
        fix="Record rules merged into 'ir.access'. Put the rule's domain in the "
            "'domain' field of an ir.access record for the same model.",
    ),
    dict(
        id="SEC005", severity="blocker",
        title="res.groups.model_access / res.groups.rule_groups removed",
        evidence="field diff on res.groups between odoo 19 and 20: "
                 "removed model_access, rule_groups; added access_ids, access_count.",
        fix="Use res.groups.access_ids (One2many to ir.access).",
    ),
    dict(
        id="SEC006", severity="warn",
        title="res.users.rules_count removed",
        evidence="field diff on res.users between odoo 19 and 20: removed rules_count.",
        fix="Count ir.access records instead.",
    ),
    dict(
        id="VIEW001", severity="blocker",
        title="<group> in a search view may not carry 'expand' or 'string'",
        evidence="verified against odoo 20 RNG validation: "
                 "RELAXNG_ERR_INVALIDATTR 'Invalid attribute expand for element group'. "
                 "Group-by filters also require domain=\"[]\".",
        fix='Use a bare <group> and give each filter domain="[]" '
            'plus context="{\'group_by\': \'field\'}".',
    ),
    dict(
        id="VIEW002", severity="blocker",
        title="<tree> is not a valid view element",
        evidence="odoo 19 and 20 core both contain zero '<tree' in addons views; "
                 "the element was renamed to <list> before 19. Modules coming from "
                 "16 or 17 still carry it.",
        fix="Rename <tree> to <list> (and </tree> to </list>).",
    ),
    dict(
        id="MAN001", severity="warn",
        title="manifest declares an older Odoo series",
        evidence="core addons use bare versions such as '1.1' in both 19 and 20, so a "
                 "bare version is valid. Only an explicit older series prefix is wrong.",
        fix="Change the leading series to 20.0, or drop the series prefix entirely.",
    ),
    dict(
        id="ENV001", severity="blocker",
        title="Odoo 20 requires PostgreSQL 16 or newer",
        evidence="odoo 20 base uses the any_value() aggregate, added in PostgreSQL 16. "
                 "On PG15 database initialisation fails with "
                 "'function any_value(integer) does not exist'.",
        fix="Upgrade the PostgreSQL server to 16+ before migrating.",
    ),
]

BY_ID = {r["id"]: r for r in RULES}
