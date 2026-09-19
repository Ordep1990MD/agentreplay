import copy
import unittest
from scripts.compare_reports import compare

class ComparisonTests(unittest.TestCase):
    def report(self):
        return {'schema_version':1,'benchmark_version':'0.1.0','results':[{'scenario':'a','checks':{'x':True,'y':False},'calls':2}]}

    def test_regression_on_already_failing_case(self):
        a=self.report();b=copy.deepcopy(a);b['results'][0]['checks']['x']=False
        self.assertEqual(compare(a,b)[0]['regressed'],['x'])

    def test_incompatible_reports_rejected(self):
        for key,value in [('benchmark_version','other'),('results',[])]:
            a=self.report();b=copy.deepcopy(a);b[key]=value
            with self.assertRaises(ValueError): compare(a,b)

    def test_improvement(self):
        a=self.report();b=copy.deepcopy(a);b['results'][0]['checks']['y']=True
        self.assertEqual(compare(a,b)[0]['improved'],['y'])
