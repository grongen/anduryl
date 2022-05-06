if __name__ == "__main__":

    # Import GUI
    from anduryl.core.main import Project
    from anduryl.ui.main import MainWindow

    import sys

    sys.path.append("test")
    from differences_all_cases import TestCompareAllCases
    from file_io import TestFromExcalibur, TestImportCSV
    from robustness import TestRobustness

    # test = TestCompareAllCases()
    # test.setUp()
    # test.test1_compare_all_cases()

    # test = TestFromExcalibur()
    # test.test1_from_excalibur()

    # test = TestRobustness()
    # test.test1_compare_item_robustness()

    test = TestImportCSV()
    test.test2_import_csv()
