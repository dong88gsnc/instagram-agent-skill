"""Functional Korean CLI regressions; no network or third-party packages."""
import json
from pathlib import Path
import subprocess
import sys
import unicodedata
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/ig-reel'))
import language_support as language
import hookscore
import beats

class KoreanWorkflow(unittest.TestCase):
    def cli(self, tool, text, *args, code=0):
        p = subprocess.run([sys.executable, str(ROOT / tool), *args], input=text,
                           text=True, capture_output=True, cwd=tempfile.gettempdir())
        self.assertEqual(p.returncode, code, p.stderr + p.stdout)
        return json.loads(p.stdout)

    def test_fifteen_second_reel(self):
        text = (ROOT/'tests/fixtures/tempur_15s_ko.txt').read_text()
        a = self.cli('skills/ig-reel/beats.py', text, '--target', '15', '--json')
        self.assertTrue(13.5 <= a['total_seconds'] <= 16.5, a)
        self.assertEqual(len(a['beats']), 5)
        self.assertTrue(all(b['dur'] > 0 for b in a['beats']))
        self.assertTrue(all(not b['flags'] for b in a['beats']))
        self.assertTrue(any('Loops:' in n for n in a['notes']))
        self.assertTrue(any('on target' in n for n in a['notes']))
        self.assertEqual(a['timing_method'], 'Hangul syllables + Latin/numeric words')

    def test_pure_korean_duration(self):
        self.assertAlmostEqual(language.duration('가나다라마'), 1)
        self.assertGreater(beats.analyse('인솔을 먼저 확인하세요.')['total_seconds'], 0)

    def test_mixed_and_normalized_text(self):
        self.assertAlmostEqual(language.duration('TEMPUR 인솔'), 2/5 + 60/165)
        self.assertEqual(language.words('템퍼 인솔'), ['템퍼', '인솔'])
        self.assertEqual(language.duration('템퍼 인솔'),
                         language.duration(unicodedata.normalize('NFD', '템퍼 인솔')))

    def test_speech_rate_override(self):
        text = (ROOT/'tests/fixtures/tempur_15s_ko.txt').read_text()
        self.assertGreater(beats.analyse(text, korean_sps=4)['total_seconds'],
                           beats.analyse(text, korean_sps=6)['total_seconds'])
        with self.assertRaises(ValueError): beats.analyse(text, korean_sps=0)
        p = subprocess.run([sys.executable, str(ROOT/'skills/ig-reel/beats.py'),
                            '--korean-sps', '0'], input=text, text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)

    def test_korean_hook_ranking(self):
        good = 'TEMPUR® 인솔, 넣기 전 확인하세요.'
        weak = '안녕하세요 여러분 오늘은 인솔 이야기를 해보겠습니다.'
        a = self.cli('skills/ig-reel/hookscore.py', good+'\n'+weak, '--json')
        self.assertGreater(a[0]['score'], a[1]['score'])
        self.assertGreater(a[0]['checks']['SPECIFICITY']['score'], 15)
        self.assertGreater(a[0]['checks']['ADDRESS']['score'], 35)
        self.assertTrue(a[1]['flags'])
        self.assertGreater(hookscore.check_specificity('세 가지를 확인하세요.')[0], 15)

    def test_humanize_korean_and_preserve_url(self):
        text = '혁신적인 TEMPUR® 인\u200b솔—착용감을 극대화하세요. https://example.com/혁신적인'
        a = self.cli('skills/ig-human/humanize.py', text, '--json')
        self.assertIn('새로운 TEMPUR® 인솔, 착용감을 높여보세요.', a['text'])
        self.assertIn('https://example.com/혁신적인', a['text'])
        self.assertNotIn('\u200b', a['text'])
        self.assertEqual(len(a['report']['lexical']), 2)
        b = self.cli('skills/ig-human/humanize.py', a['text'], '--json')
        self.assertEqual(a['text'], b['text'])

    def test_detector_does_not_claim_korean_validation(self):
        text = (ROOT/'tests/fixtures/tempur_15s_ko.txt').read_text()
        a = self.cli('skills/ig-human/detect.py', text, '--json')
        self.assertEqual(a['verdict'], 'REVIEW')
        self.assertNotIn('empty', a['checks']['SLOP DENSITY']['detail'])
        dirty = self.cli('skills/ig-human/detect.py', '혁신적인 인솔을 선택하세요.', '--json')
        self.assertLess(dirty['checks']['SLOP DENSITY']['score'], 100)

    def test_english_regression(self):
        self.assertEqual(hookscore.run('I lost $18,000 because of one missing contract.')[2], 'STRONG')
        self.assertEqual(beats.analyse('I lost $18,000.')['total_words'], 3)
        self.assertAlmostEqual(beats.analyse('I lost $18,000.')['total_seconds'], 1.09)
        a = self.cli('skills/ig-human/humanize.py', 'Let us delve into this.', '--json')
        self.assertNotIn('delve', a['text'])

    def test_installer_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            args = [sys.executable, str(ROOT/'scripts/install_codex_skills.py'), '--skills-dir', directory]
            for _ in range(2):
                p = subprocess.run(args, text=True, capture_output=True)
                self.assertEqual(p.returncode, 0, p.stderr)
            for name in ('ig-reel', 'ig-human'):
                self.assertEqual((Path(directory)/name/'SKILL.md').read_bytes(),
                                 (ROOT/'skills'/name/'SKILL.md').read_bytes())

    def test_installer_preserves_local_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            args = [sys.executable, str(ROOT/'scripts/install_codex_skills.py'), '--skills-dir', directory]
            subprocess.run(args, check=True, capture_output=True)
            path = Path(directory)/'ig-human/SKILL.md'
            path.write_text('local user edits')
            p = subprocess.run(args, text=True, capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(path.read_text(), 'local user edits')

    def test_installer_preserves_symlink_target(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)/'skills'
            external = Path(directory)/'user-file'
            external.write_text('user data')
            (destination/'ig-reel').mkdir(parents=True)
            (destination/'ig-reel/SKILL.md').symlink_to(external)
            p = subprocess.run([sys.executable, str(ROOT/'scripts/install_codex_skills.py'),
                                '--skills-dir', str(destination)], capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(external.read_text(), 'user data')
            self.assertFalse((destination/'ig-human').exists())

    def test_humanizer_preserves_decomposed_url(self):
        url = 'https://example.com/' + unicodedata.normalize('NFD', '혁신적인')
        a = self.cli('skills/ig-human/humanize.py', '혁신적인 인솔 ' + url, '--json')
        self.assertIn(url, a['text'])
        self.assertTrue(a['text'].startswith('새로운 인솔'))

    def test_english_detector_word_count_preserved(self):
        path = ROOT/'skills/ig-human/detect.py'
        import importlib.util
        spec = importlib.util.spec_from_file_location('human_detector', path)
        detector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(detector)
        self.assertEqual(detector.words('I paid $18,000 for two contracts.'),
                         ['I', 'paid', 'for', 'two', 'contracts'])

    def test_codex_registration_paths(self):
        for name in ('ig-reel', 'ig-human'):
            path = ROOT/'.agents/skills'/name
            self.assertTrue(path.is_symlink())
            self.assertEqual(path.resolve(), ROOT/'skills'/name)
            self.assertTrue((path/'SKILL.md').is_file())

if __name__ == '__main__':
    unittest.main()
