"""Count-unit regressions with generic statistics, without sequence data."""
from io import StringIO
import pytest
from bonsai_libs.parse.models.enums import AnalysisType
from bonsai_libs.parse.parsers.post_align_qc import SamtoolsQcParser


@pytest.mark.parametrize('reads,paired_reads,pairs',[(20,0,0),(2,2,1),(20,20,10),(24,20,10)])
def test_read_pairs_are_counted_in_pairs(reads,paired_reads,pairs):
    source=StringIO(f'SN\traw total sequences:\t{reads}\nSN\treads paired:\t{paired_reads}\n')
    result=SamtoolsQcParser().parse(source).results[AnalysisType.QC]
    assert result.status=='parsed'
    assert result.value.n_reads==reads
    assert result.value.n_read_pairs==pairs
