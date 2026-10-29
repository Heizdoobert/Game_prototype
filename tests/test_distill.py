import os, shutil, tempfile, unittest
from apk2proto import distill

DUMP = '''// Image 0: Assembly-CSharp.dll - 0
// Image 1: mscorlib.dll - 3
// Namespace:
public class BoardController : MonoBehaviour // TypeDefIndex: 0
{
	// Fields
	private const int MaxSlots = 5;
	public int slotCount; // 0x20
	// Methods
	// RVA: 0x10 Offset: 0x10 VA: 0x10
	public void AddSlot() { }
}
// Namespace:
public enum ColorType // TypeDefIndex: 1
{
	// Fields
	public byte value__; // 0x0
	public const ColorType Blue = 0;
	public const ColorType Red = 1;
}
// Namespace:
public class PausePopup : Popup // TypeDefIndex: 2
{
}
// Namespace: System
public class String // TypeDefIndex: 3
{
	public const int MaxLen = 9;
}
'''

def write(d, rel, text):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh: fh.write(text)
    return p

class ParseDumpTests(unittest.TestCase):
    def test_parse_first_assembly_only(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        types = distill.parse_dump(write(d, 'dump.cs', DUMP))
        self.assertEqual([t['name'] for t in types], ['BoardController', 'ColorType', 'PausePopup'])
        b, e = types[0], types[1]
        self.assertEqual(b['consts'], {'MaxSlots': '5'})
        self.assertEqual(b['fields'], [['int', 'slotCount', '20']])
        self.assertEqual(b['methods'], ['AddSlot'])
        self.assertEqual((e['kind'], e['members']), ('enum', {'Blue': '0', 'Red': '1'}))

    def parse_text(self, text):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return distill.parse_dump(write(d, 'dump.cs', text))

    def test_generic_type_name_kept(self):
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            '// Namespace: \n'
            'public class BasePackData<TConfig, TRemoteReward> : Base // TypeDefIndex: 0\n'
            '{\n'
            '}\n')
        self.assertEqual([t['name'] for t in types], ['BasePackData<TConfig, TRemoteReward>'])

    def test_generic_field_type_kept(self):
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            'public class Board // TypeDefIndex: 0\n'
            '{\n'
            '\tpublic Dictionary<ColorType, int> slotByColor; // 0x58\n'
            '}\n')
        self.assertEqual(types[0]['fields'], [['Dictionary<ColorType, int>', 'slotByColor', '58']])

    def test_unparsed_header_does_not_leak_members(self):
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            'public class Prev // TypeDefIndex: 0\n'
            '{\n'
            '\tpublic int own; // 0x10\n'
            '}\n'
            'weird header // TypeDefIndex: 7\n'
            '{\n'
            '\tpublic int leaked; // 0x18\n'
            '}\n')
        self.assertEqual([t['name'] for t in types], ['Prev'])
        self.assertEqual(types[0]['fields'], [['int', 'own', '10']])

    def test_single_image_dump_returns_all_types(self):
        # no "// Image 1:" line: fail-open, nothing is cut off
        types = self.parse_text(
            '// Image 0: Assembly-CSharp.dll - 0\n'
            'public class A // TypeDefIndex: 0\n'
            '{\n'
            '}\n'
            'public class B // TypeDefIndex: 1\n'
            '{\n'
            '}\n')
        self.assertEqual([t['name'] for t in types], ['A', 'B'])

if __name__ == '__main__': unittest.main()
