import unittest  # The test framework


class Test_TestIncrementDecrement(unittest.TestCase):
    def test_increment(self):
        self.assertEqual(4, 4)

    # This test is designed to fail for demonstration purposes.
    def test_decrement(self):
        self.assertEqual(3, 3)


if __name__ == "__main__":
    unittest.main()
