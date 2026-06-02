"""Custom exceptions for the Bonsai API."""

from prp.parse.exceptions import ParserError, UnsupportedVersionError, UnsupportedSoftwareError, UnsupportedAnalysisTypeError, InvalidDataFormat, SchemaMismatchError


class DomainError(Exception):
    """Raised when there is a domain-specific error."""


class EntryNotFound(DomainError):
    """Raised when a requested entry is not found in the database."""


class UserNotFound(EntryNotFound):
    """Raised when a requested user is not found in the database."""


class DatabaseOperationError(DomainError):
    """Generic database operation error for CRUD functions.

    Use this for any unexpected database-level failure (connection issues,
    write errors, bulk write failures, etc.) so callers can handle a single
    exception type for database errors.
    """


class ConflictError(DomainError):
    """Raised when a resource conflict occurs."""


class AuditLogError(DomainError):
    """Raised when an audit log operation fails."""


class ForbiddenAccess(DomainError):
    """Raised when a resource access is forbidden."""


class AnalysisExistsError(Exception):
    """Raised when a duplicate analysis already exists for a sample."""


class GenomeResourceError(DomainError):
    """Raised when there is an error resolving a genome resource."""


class InvalidRangeError(Exception):
    """Exception for retrieving invalid file ranges."""


class RangeOutOfBoundsError(Exception):
    """Exception if range is out of bounds."""


class MigrationError(Exception):
    """Raised when a migration operation fails."""

