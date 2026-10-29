import unittest
from apk2proto.schema import validate

def good():
    return {'app': {'package': 'a.b', 'engine': 'Unity', 'version': '1'}, 'enums': {}, 'constants': {},
            'config': [], 'classes': [], 'levels': {}, 'strings': [], 'screens': [], 'secrets': [], 'coverage': {}}

class SchemaTests(unittest.TestCase):
    def test_good_passes(self): validate(good())

    def test_missing_and_wrong_types_listed(self):
        s = good(); del s['enums']; s['classes'] = {}
        with self.assertRaises(ValueError) as cm: validate(s)
        self.assertIn('enums', str(cm.exception)); self.assertIn('classes', str(cm.exception))

    def test_secret_entry_must_not_carry_a_value(self):
        s = good(); s['secrets'] = [{'file': 'f', 'key': 'k', 'value': 'hunter2'}]
        with self.assertRaises(ValueError): validate(s)

    def test_app_fields_required(self):
        s = good(); s['app'] = {'package': 'a.b'}
        with self.assertRaises(ValueError): validate(s)

if __name__ == '__main__': unittest.main()
