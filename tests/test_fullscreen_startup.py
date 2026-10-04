import ast
import unittest
from pathlib import Path


class FullscreenStartupTests(unittest.TestCase):
    def test_only_display_creation_uses_native_fullscreen(self):
        source = Path(__file__).resolve().parents[1] / "src" / "main.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "set_mode"]
        # Neither resize events nor starting a new session recreate a window.
        self.assertEqual(len(calls), 1)
        self.assertEqual(ast.literal_eval(calls[0].args[0]), (0, 0))
        self.assertEqual(calls[0].args[1].attr, "FULLSCREEN")


if __name__ == "__main__":
    unittest.main()
