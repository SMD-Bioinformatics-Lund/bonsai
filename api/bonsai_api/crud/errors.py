"""Errors used by CRUD functions.

This module defines a small set of exception types used by CRUD helpers.
Use `EntryNotFound` for missing documents, `DocumentExistsError` when a
create operation violates uniqueness, and `DatabaseOperationError` for
generic database-side errors that can be raised by multiple CRUD functions.
"""


class EntryNotFound(Exception):
    """Document not found in the database."""


class DatabaseOperationError(Exception):
    """Generic database operation error for CRUD functions.

    Use this for any unexpected database-level failure (connection issues,
    write errors, bulk write failures, etc.) so callers can handle a single
    exception type for database errors.
    """


class DocumentExistsError(Exception):
    """Raised when trying to create a document that already exists."""
