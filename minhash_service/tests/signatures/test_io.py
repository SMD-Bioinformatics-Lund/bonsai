"""Test reading and writing signatures to disk."""

import os
import tempfile
from pathlib import Path

import pytest

from minhash_service.core.exceptions import SignatureNotFoundError
from minhash_service.signatures.io import read_signatures, write_signatures


@pytest.fixture()
def sig_file_single_kmer(data_dir: Path) -> Path:
    """Provide a signature file with a single kmer size."""
    return data_dir / "DRR237260.sig"


@pytest.fixture()
def sig_content_single_kmer(sig_file_single_kmer: Path) -> str:
    """Read signature file content as JSON string."""
    return sig_file_single_kmer.read_text(encoding="utf-8")


@pytest.fixture()
def sig_file_duplicate(data_dir: Path) -> Path:
    """Provide a duplicate signature file."""
    return data_dir / "DRR237260.dupl.sig"


class TestReadSignatures:
    """Test reading signatures from disk."""

    def test_read_signatures_all_kmers(self, sig_file_single_kmer: Path):
        """Read all kmers from signature file."""
        sigs = read_signatures(sig_file_single_kmer)

        assert len(sigs) > 0
        # File contains both kmer=31 and kmer=51
        kmers = {sig.minhash.ksize for sig in sigs}
        assert 31 in kmers
        assert 51 in kmers

    def test_read_signatures_filter_kmer_31(self, sig_file_single_kmer: Path):
        """Read only kmer=31 signatures."""
        sigs = read_signatures(sig_file_single_kmer, kmer_size=31)

        assert len(sigs) > 0
        # All signatures should be kmer=31
        for sig in sigs:
            assert sig.minhash.ksize == 31

    def test_read_signatures_filter_kmer_51(self, sig_file_single_kmer: Path):
        """Read only kmer=51 signatures."""
        sigs = read_signatures(sig_file_single_kmer, kmer_size=51)

        assert len(sigs) > 0
        # All signatures should be kmer=51
        for sig in sigs:
            assert sig.minhash.ksize == 51

    def test_read_signatures_kmer_mismatch_raises(
        self, sig_file_single_kmer: Path
    ):
        """Reading non-existent kmer size raises error."""
        with pytest.raises(SignatureNotFoundError, match="No signatures"):
            read_signatures(sig_file_single_kmer, kmer_size=99)

    def test_read_signatures_preserves_metadata(self, sig_file_single_kmer: Path):
        """Signature metadata is preserved on read."""
        sigs = read_signatures(sig_file_single_kmer, kmer_size=31)

        sig = sigs[0]
        assert sig.name == "DRR237260"
        assert sig.md5sum() is not None

    def test_read_signatures_invalid_path_raises(self):
        """Reading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            read_signatures(Path("/nonexistent/path/sig.sig"))


class TestWriteSignatures:
    """Test writing signatures to disk."""

    def test_write_signatures_creates_file(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Write signatures to disk creates file."""
        output_path = tmp_path / "output.sig"

        result = write_signatures(path=output_path, signature=sig_content_single_kmer)

        assert result == output_path
        assert output_path.exists()

    def test_write_signatures_roundtrip(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Write and read back preserves signature."""
        output_path = tmp_path / "output.sig"
        write_signatures(path=output_path, signature=sig_content_single_kmer)

        # Read back
        sigs = read_signatures(output_path)

        assert len(sigs) > 0

    def test_write_signatures_roundtrip_all_kmers(
        self, sig_file_single_kmer: Path, tmp_path: Path
    ):
        """Roundtrip preserves all kmer sizes."""
        sig_content = sig_file_single_kmer.read_text(encoding="utf-8")
        output_path = tmp_path / "output.sig"

        # Write signatures
        write_signatures(path=output_path, signature=sig_content)

        # Read back all kmers
        sigs = read_signatures(output_path)
        kmers = {sig.minhash.ksize for sig in sigs}

        # Should have both kmers
        assert 31 in kmers
        assert 51 in kmers

    def test_write_signatures_filter_kmer_on_write(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Write only specific kmer size."""
        output_path = tmp_path / "output_k31.sig"

        write_signatures(
            path=output_path, signature=sig_content_single_kmer, kmer_size=31
        )

        # Read back and verify only kmer=31
        sigs = read_signatures(output_path)
        for sig in sigs:
            assert sig.minhash.ksize == 31

    def test_write_signatures_with_name(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Write signatures with custom name."""
        output_path = tmp_path / "named.sig"
        custom_name = "my_custom_sample"

        write_signatures(
            path=output_path, signature=sig_content_single_kmer, name=custom_name
        )

        # Read back and verify name
        sigs = read_signatures(output_path)
        for sig in sigs:
            assert sig.name == custom_name

    def test_write_signatures_preserves_checksum(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Signature checksums are preserved on write/read."""
        # Read original
        output_path_1 = tmp_path / "sig1.sig"
        write_signatures(path=output_path_1, signature=sig_content_single_kmer)
        sigs_1 = read_signatures(output_path_1, kmer_size=31)

        # Write again
        output_path_2 = tmp_path / "sig2.sig"
        # Get the original signature content for second write
        write_signatures(path=output_path_2, signature=sig_content_single_kmer)
        sigs_2 = read_signatures(output_path_2, kmer_size=31)

        # Checksums should match
        assert sigs_1[0].md5sum() == sigs_2[0].md5sum()

    def test_write_signatures_permission_error(self, sig_content_single_kmer: str, tmp_path: Path):
        """Write to read-only location raises PermissionError."""
        # Use /dev/null or similar read-only location
        readonly_path = tmp_path / "file.txt"
        readonly_path.touch(mode=0o444)

        with pytest.raises(PermissionError):
            write_signatures(
                path=readonly_path, signature=sig_content_single_kmer
            )


class TestKmerFilteringMultiKmer:
    """Test kmer filtering with multi-kmer scenarios."""

    def test_read_multiple_files_different_kmers(
        self, sig_file_single_kmer: Path, tmp_path: Path
    ):
        """Read multiple files with different kmers."""
        sig_content = sig_file_single_kmer.read_text(encoding="utf-8")

        # Write kmer=31 variant
        file_k31 = tmp_path / "sig_k31.sig"
        write_signatures(path=file_k31, signature=sig_content, kmer_size=31)

        # Write kmer=51 variant
        file_k51 = tmp_path / "sig_k51.sig"
        write_signatures(path=file_k51, signature=sig_content, kmer_size=51)

        # Read them separately
        sigs_k31 = read_signatures(file_k31)
        sigs_k51 = read_signatures(file_k51)

        # Verify they only contain their kmers
        assert all(sig.minhash.ksize == 31 for sig in sigs_k31)
        assert all(sig.minhash.ksize == 51 for sig in sigs_k51)

    def test_write_kmer_then_read_different_kmer_fails(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Reading different kmer than written raises error."""
        output_path = tmp_path / "sig_k31_only.sig"

        # Write only kmer=31
        write_signatures(
            path=output_path, signature=sig_content_single_kmer, kmer_size=31
        )

        # Try to read kmer=51 (not in file)
        with pytest.raises(SignatureNotFoundError):
            read_signatures(output_path, kmer_size=51)

    def test_no_kmer_filter_reads_all(
        self, sig_file_single_kmer: Path, tmp_path: Path
    ):
        """Reading without kmer filter gets all kmers."""
        sig_content = sig_file_single_kmer.read_text(encoding="utf-8")
        output_path = tmp_path / "all_kmers.sig"

        write_signatures(path=output_path, signature=sig_content)

        # Read without filter
        sigs = read_signatures(output_path)
        kmers = {sig.minhash.ksize for sig in sigs}

        # Should have multiple kmers
        assert len(kmers) > 1
        assert 31 in kmers
        assert 51 in kmers


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_write_signatures_creates_parent_directories(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Write creates parent directories if needed."""
        nested_path = tmp_path / "nested" / "dir" / "sig.sig"

        result = write_signatures(
            path=nested_path, signature=sig_content_single_kmer
        )

        assert result.exists()

    def test_read_write_maintains_signature_integrity(
        self, sig_file_single_kmer: Path, tmp_path: Path
    ):
        """Signature data integrity through write/read cycle."""
        sig_content = sig_file_single_kmer.read_text(encoding="utf-8")
        output_path = tmp_path / "integrity_test.sig"

        write_signatures(path=output_path, signature=sig_content)
        sigs = read_signatures(output_path)

        # Verify signature has valid hash values
        for sig in sigs:
            assert sig.minhash.moltype == "DNA"
            assert sig.minhash.ksize in [31, 51]

    def test_multiple_write_overwrites(
        self, sig_content_single_kmer: str, tmp_path: Path
    ):
        """Multiple writes to same file overwrites."""
        output_path = tmp_path / "overwrite.sig"

        # First write
        write_signatures(path=output_path, signature=sig_content_single_kmer)
        sigs_1 = read_signatures(output_path, kmer_size=31)

        # Second write with different kmer filter
        write_signatures(
            path=output_path,
            signature=sig_content_single_kmer,
            kmer_size=51
        )
        sigs_2 = read_signatures(output_path, kmer_size=51)

        # File should now only have kmer=51
        with pytest.raises(SignatureNotFoundError):
            read_signatures(output_path, kmer_size=31)
