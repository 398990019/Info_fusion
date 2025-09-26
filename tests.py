import unittest
from simhash_utils import generate_simhash, get_hamming_distance
from diff_utils import find_diff

class TestSimHashUtils(unittest.TestCase):
    def test_generate_simhash(self):
        text1 = "这是一个测试文本"
        text2 = "这是另一个测试文本"
        
        hash1 = generate_simhash(text1)
        hash2 = generate_simhash(text2)
        
        self.assertIsNotNone(hash1)
        self.assertIsNotNone(hash2)
        self.assertNotEqual(hash1.value, hash2.value)

class TestDiffUtils(unittest.TestCase):
    def test_find_diff(self):
        old_text = "这是第一行\n这是第二行\n这是第三行"
        new_text = "这是第一行\n这是修改后的第二行\n这是第三行"
        
        diff = find_diff(old_text, new_text)
        self.assertIn("修改后的第二行", diff)

if __name__ == '__main__':
    unittest.main()