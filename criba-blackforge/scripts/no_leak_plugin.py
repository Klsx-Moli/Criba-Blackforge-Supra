import sys
def pytest_configure(config):
    for f in list(sys.meta_path):
        if type(f).__name__ == '_EditableFinder':
            sys.meta_path.remove(f)
