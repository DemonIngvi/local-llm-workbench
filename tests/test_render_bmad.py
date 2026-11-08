import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('render_bmad', Path(__file__).parents[1] / 'scripts' / 'render_bmad.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class RenderTests(unittest.TestCase):
    def test_escaping_and_markup(self):
        value = renderer.markdown('# Заголовок\n\n- **важно** `<script>`\n- [ссылка](https://example.com)')
        self.assertIn('<h2>Заголовок</h2>', value)
        self.assertIn('<strong>важно</strong>', value)
        self.assertIn('&lt;script&gt;', value)
        self.assertNotIn('<script>', value)
        self.assertIn('href="https://example.com"', value)

    def test_unknown_url_not_rendered_as_link(self):
        self.assertNotIn('<a ', renderer.markdown('[x](javascript:alert)'))

    def test_all_current_documents_render(self):
        files = renderer.source_files()
        self.assertGreaterEqual(len(files), 7)
        output = renderer.render(files)
        self.assertIn('lang="ru"', output)
        self.assertEqual(output.count('class="document"'), len(files))


if __name__ == '__main__':
    unittest.main()
