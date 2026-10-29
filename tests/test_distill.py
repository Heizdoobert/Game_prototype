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

if __name__ == '__main__': unittest.main()
