#!/usr/bin/env python3
"""Check generated sketches in the MinHash image, without a running stack."""
from collections import Counter
from pathlib import Path

import sourmash

ROOT = Path(__file__).resolve().parent


def load(path):
    signatures = list(sourmash.load_file_as_signatures(str(path)))
    assert len(signatures) == 1, path
    signature = signatures[0]
    assert signature.minhash.ksize == 31 and signature.minhash.scaled == 1000
    assert len(signature.minhash) > 0
    return signature


baseline = load(ROOT / "samples/synthetic_tb_001/synthetic_tb_001.sig")
identical = load(ROOT / "cases/genomes/synthetic_identical.sig")
unrelated = load(ROOT / "cases/genomes/synthetic_unrelated.sig")
deletion = load(ROOT / "cases/genomes/synthetic_deletion.sig")
assert baseline.md5sum() == identical.md5sum()
assert baseline.minhash.jaccard(unrelated.minhash) == 0
assert 0 < baseline.minhash.jaccard(deletion.minhash) < 1
for prefix in ("tb", "sa"):
    paths = sorted((ROOT / "samples").glob(f"synthetic_{prefix}_*/*.sig"))
    checksums = Counter(load(path).md5sum() for path in paths)
    print(f"PASS {prefix}: {len(paths)} samples, {len(checksums)} distinct sketches; shared sketches deliberately exercise sample mapping")
print("PASS index cases: identical checksum, unrelated genome, intermediate deletion similarity")
