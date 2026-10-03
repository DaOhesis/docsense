"""Test configuration.

Sets up:
- A throwaway SQLite database (tempfile) per test session.
- A throwaway upload directory (tempfile) per test session.
Both are set via env vars BEFORE any docint module is imported,
so SQLAlchemy and the API pick up the right paths.
"""
import os
import tempfile

# Must be set before any docint import so SQLAlchemy binds the right DB.
_tmp_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp_dir}/uploads"
