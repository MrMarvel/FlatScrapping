import os


class TempFile:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.path):
            os.remove(self.path)
