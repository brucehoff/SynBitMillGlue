'''
Created on Jun 6, 2013

@author: brucehoff
'''
import unittest
from createUserNameMod import createUserName

class Test(unittest.TestCase):


    def testCreateName(self):
        self.assertEqual(createUserName("First", "Last", "101", 21), "101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 22), "101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 23), "l.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 26), "last.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 27), "last.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 28), "f.last.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 29), "fi.last.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 32), "first.last.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 33), "first.last.101.wcpe.sagebase.org")
        self.assertEqual(createUserName("First", "Last", "101", 100), "first.last.101.wcpe.sagebase.org")
        
        self.assertEqual(createUserName("Fi@#$%rst", "L.-_", "101", 100), "first.l.-_.101.wcpe.sagebase.org")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()