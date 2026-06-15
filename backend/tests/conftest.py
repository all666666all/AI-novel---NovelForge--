"""Shared test configuration.

Environment variables must be set before any ``app.*`` module is imported,
because settings are read once at import time. pytest imports this file before
collecting the test modules, so this is the right place to do it.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost")
os.environ.setdefault("DB_PROVIDER", "sqlite")
# Enables the vector-store code paths (the tests use in-memory stubs, never a real DB).
os.environ.setdefault("VECTOR_DB_URL", "file:./storage/test_vectors.db")
