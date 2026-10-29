import unittest
from apk2proto.textutil import clip, is_il2cpp, leaves, secret_pairs, secret_value

class ClipTests(unittest.TestCase):
    def test_clips_strings_and_keys_everywhere(self):
        out = clip({'k' * 10: ['a' * 10, {'b' * 10: 'c' * 10, 'n': 5}], 'f': 1.5, 'z': None}, 4)
        self.assertEqual(out, {'kkkk': ['aaaa', {'bbbb': 'cccc', 'n': 5}], 'f': 1.5, 'z': None})

    def test_short_input_unchanged_and_original_untouched(self):
        src = {'a': ['bc']}
        self.assertEqual(clip(src, 10), src); clip(src, 1); self.assertEqual(src, {'a': ['bc']})

class Il2cppTests(unittest.TestCase):
    def test_prefix_only(self):
        self.assertTrue(is_il2cpp('Unity\nIL2CPP -> use bin/il2cpp_dump.sh\n'))
        self.assertFalse(is_il2cpp('Unity\nMono: Assembly-CSharp.dll present -> decompile (no IL2CPP step)\n'))
        self.assertFalse(is_il2cpp(''))

class SecretTests(unittest.TestCase):
    def test_eligibility(self):
        for ok in ('abcdefgh', 'ab12', 'a1b2c', 1234567, '<x>1234'): self.assertEqual(secret_value(ok), str(ok))
        for bad in ('abc', 'abcdefg', 'true', 'FALSE', 'None', 'yes', '<REDACTED>', 'ab', 12345, True, None, 1.5, ['a1b2c3d4']): self.assertIsNone(secret_value(bad))

    def test_leaves_skip_bools_and_none(self):
        self.assertEqual(sorted(map(str, leaves({'a': [1, 'x', True, None], 'b': {'c': 2.5}}))), ['1', '2.5', 'x'])

    def test_secret_pairs_dict_list_and_kv_shapes(self):
        pred = lambda k: 'pass' in k.lower()
        node = {'passA': {'n': ['v1', 2]}, 'ok': [{'key': 'myPass', 'value': 'v3'}, {'Name': 'plain', 'Value': 'no'}], 'z': {'passB': 'v4'}}
        self.assertEqual(sorted((n, str(v)) for n, v in secret_pairs(node, pred)), [('myPass', 'v3'), ('passA', '2'), ('passA', 'v1'), ('passB', 'v4')])

if __name__ == '__main__': unittest.main()
