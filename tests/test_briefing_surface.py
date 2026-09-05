from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BriefingSurfaceTests(unittest.TestCase):
    def test_briefing_surface_and_hash_contract(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'js' / 'app.js').read_text(encoding='utf-8')
        for element_id in (
            'comparison-briefing', 'briefing-view', 'briefing-scope', 'briefing-kpis',
            'briefing-cinemas', 'briefing-trajectory-table', 'briefing-decisions',
            'briefing-copy-link', 'briefing-exit'
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn("params.get('brief') === '1'", js)
        self.assertIn("params.set('brief','1')", js)
        self.assertIn("document.body.classList.toggle('briefing-mode'", js)
        self.assertIn('renderBriefing();', js)


if __name__ == '__main__':
    unittest.main()
