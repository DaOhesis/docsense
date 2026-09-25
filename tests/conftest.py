import os
import tempfile

# Use a throwaway DB for tests (must be set before importing the app)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
