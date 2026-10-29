import unittest
from apk2proto.textutil import clip

class ClipTests(unittest.TestCase):
    def test_clips_strings_and_keys_everywhere(self):
        out = clip({'k' * 10: ['a' * 10, {'b' * 10: 'c' * 10, 'n': 5}], 'f': 1.5, 'z': None}, 4)
        self.assertEqual(out, {'kkkk': ['aaaa', {'bbbb': 'cccc', 'n': 5}], 'f': 1.5, 'z': None})

    def test_short_input_unchanged_and_original_untouched(self):
        src = {'a': ['bc']}
        self.assertEqual(clip(src, 10), src); clip(src, 1); self.assertEqual(src, {'a': ['bc']})

if __name__ == '__main__': unittest.main()
