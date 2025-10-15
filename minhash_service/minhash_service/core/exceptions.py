"""Minhash service exceptions."""


class SampleNotFoundError(Exception):
    """Raised when a sample is not found."""


class SignatureNotFoundError(Exception):
    """Raised when a signature is not found."""


class FileRemovalError(Exception):
    """Raised when a file could not be removed from the filesystem."""

    def __init__(self, filepath: str, reason: str = ""):
        message = f"Failed to remove file: {filepath}"
        if reason:
            message += f" | Reason: {reason}"
        super().__init__(message)
        self.filepath = filepath
        self.reason = reason
