import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from xml.etree import ElementTree

spec = importlib.util.spec_from_file_location(
    "cards", Path(__file__).parents[1] / "scripts/generate_cards.py"
)
cards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cards)


class GenerateCardsTests(unittest.TestCase):
    def api(self, path):
        if path.startswith("search/issues?"):
            return {
                "total_count": 8 if "is%3Amerged" in path else 10,
                "incomplete_results": False,
            }
        name = path.rsplit("/", 1)[-1]
        return {
            "name": name,
            "full_name": f"shenweichen/{name}",
            "private": False,
            "description": '<script>alert("test")</script> & repository',
            "language": "Python",
            "stargazers_count": 100,
            "forks_count": 5,
        }

    def test_cards_escape_api_text_and_show_correct_statistics(self):
        result = cards.generate("shenweichen", api=self.api)
        self.assertEqual(len(result), 5)
        for content in result.values():
            root = ElementTree.fromstring(content)
            self.assertFalse(root.findall(".//{http://www.w3.org/2000/svg}script"))
        self.assertIn("80.0%", result["stats.svg"])
        self.assertIn(">400</text>", result["stats.svg"])
        self.assertIn("&lt;script&gt;", result["deepctr_pin.svg"])

    def test_incomplete_search_results_fail(self):
        def api(path):
            result = copy.deepcopy(self.api(path))
            if path.startswith("search/issues?"):
                result["incomplete_results"] = True
            return result
        with self.assertRaisesRegex(ValueError, "incomplete"):
            cards.generate("shenweichen", api=api)

    def test_network_failure_preserves_existing_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            saved = Path(directory, "stats.svg")
            saved.write_text("existing valid card")
            with patch.object(sys, "argv", [
                "generate_cards.py", "--owner", "shenweichen", "--output", directory
            ]), patch.object(cards, "urlopen", side_effect=URLError("unavailable")):
                with self.assertRaises(URLError):
                    cards.main()
            self.assertEqual(saved.read_text(), "existing valid card")
            self.assertEqual(list(Path(directory).iterdir()), [saved])


if __name__ == "__main__":
    unittest.main()
