import pathlib, sys, tempfile, textwrap, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from odoo20check.scanner import scan_module


def build(root, name, files):
    d = pathlib.Path(root) / name
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content))
    return d


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def ids(self, mod):
        return sorted({f.rule_id for f in scan_module(mod)})

    def test_clean_v20_module_is_silent(self):
        m = build(self.root, "clean", {
            "__manifest__.py": "{'name': 'x', 'version': '20.0.1.0.0', 'depends': ['base']}",
            "security/ir.access.csv": "id,name,model_id/id,group_id/id,operation,domain\na,b,c,d,crud,\n",
            "views/v.xml": "<odoo><record id='a' model='ir.ui.view'><field name='arch' type='xml'>"
                           "<list><field name='x'/></list></field></record></odoo>",
        })
        self.assertEqual(self.ids(m), [])

    def test_old_security_csv(self):
        m = build(self.root, "old", {
            "__manifest__.py": "{'name': 'x', 'version': '1.0'}",
            "security/ir.model.access.csv":
                "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n",
        })
        self.assertIn("SEC001", self.ids(m))
        self.assertIn("SEC002", self.ids(m))

    def test_removed_models_detected(self):
        m = build(self.root, "models", {
            "__manifest__.py": "{'name': 'x', 'version': '1.0'}",
            "models/a.py": "def f(env):\n    env['ir.model.access'].check('x')\n    env['ir.rule'].search([])\n",
            "security/r.xml": "<odoo><record id='r' model='ir.rule'><field name='name'>n</field></record></odoo>",
        })
        ids = self.ids(m)
        self.assertIn("SEC003", ids)
        self.assertIn("SEC004", ids)

    def test_comments_do_not_trigger(self):
        """Prose about ir.rule in a comment is not a code reference."""
        m = build(self.root, "comment", {
            "__manifest__.py": "{'name': 'x', 'version': '1.0'}",
            "models/a.py": "# we used to use 'ir.rule' here but no longer do\nX = 1\n",
        })
        self.assertEqual(self.ids(m), [])

    def test_upgrade_scripts_skipped(self):
        """Migration scripts reference removed models on purpose."""
        m = build(self.root, "upg", {
            "__manifest__.py": "{'name': 'x', 'version': '1.0'}",
            "upgrades/1.0/pre-migrate.py": "q = \"AND d.model = 'ir.rule'\"\n",
        })
        self.assertEqual(self.ids(m), [])

    def test_bare_version_is_valid(self):
        """Core addons use bare versions like 1.1; only an older series is wrong."""
        m = build(self.root, "bare", {"__manifest__.py": "{'name': 'x', 'version': '1.1'}"})
        self.assertNotIn("MAN001", self.ids(m))
        m2 = build(self.root, "old_series", {"__manifest__.py": "{'name': 'x', 'version': '17.0.1.0.0'}"})
        self.assertIn("MAN001", self.ids(m2))

    def test_search_group_attrs(self):
        m = build(self.root, "search", {
            "__manifest__.py": "{'name': 'x', 'version': '1.0'}",
            "views/s.xml": "<odoo><record id='s' model='ir.ui.view'><field name='arch' type='xml'>"
                           "<search><group expand='0' string='Group By'>"
                           "<filter name='f' context=\"{'group_by':'x'}\"/></group></search>"
                           "</field></record></odoo>",
        })
        self.assertIn("VIEW001", self.ids(m))

    def test_tree_element(self):
        m = build(self.root, "tree", {
            "__manifest__.py": "{'name': 'x', 'version': '1.0'}",
            "views/t.xml": "<odoo><record id='t' model='ir.ui.view'><field name='arch' type='xml'>"
                           "<tree><field name='x'/></tree></field></record></odoo>",
        })
        self.assertIn("VIEW002", self.ids(m))


if __name__ == "__main__":
    unittest.main(verbosity=2)
