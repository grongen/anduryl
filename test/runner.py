import unittest
import sys

import differences_all_cases
import robustness

# initialize the test suite
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# add tests to the test suite
suite.addTests(loader.loadTestsFromModule(differences_all_cases))
suite.addTests(loader.loadTestsFromModule(robustness))

# initialize a runner, pass it your suite and run it
runner = unittest.TextTestRunner(verbosity=3)

if (len(sys.argv) > 1) and (sys.argv[1] == 'timeit'):
        
    import cProfile, pstats, io
    pr = cProfile.Profile()
    pr.enable()

    result = runner.run(suite)

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    with open('profile.txt', 'w') as f:
        f.write(s.getvalue())

else:
    result = runner.run(suite)

