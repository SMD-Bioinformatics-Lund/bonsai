"""Define cofiguration of IGVjs."""

from enum import StrEnum
from pydantic import Field, BaseModel, ConfigDict

class IgvDisplayMode(StrEnum):
    """Valid display modes."""

    COLLAPSED = "COLLAPSED"
    EXPANDED = "EXPANDED"
    SQUISHED = "SQUISHED"


class IgvBase(BaseModel):

    model_config = ConfigDict(
        populate_by_name=True,
        ser_json_exclude_none=True
    )


class IgvTrack(IgvBase):
    """Generic IGV track model."""

    name: str
    type: str                      # "alignment", "variant", "annotation"
    format: str | None = None

    source_type: str = Field("file", alias="sourceType")
    url: str
    index_url: str | None = Field(None, alias="indexURL")

    order: int = 1
    height: int = 50
    auto_height: bool = Field(False, alias="autoHeight")
    min_height: int = Field(50, alias="minHeight")
    max_height: int = Field(500, alias="maxHeight")

    display_mode: IgvDisplayMode = Field(
        IgvDisplayMode.COLLAPSED,
        alias="displayMode"
    )

    # optional extras
    show_soft_clips: bool | None = Field(default=None, alias="showSoftClips")
    name_field: str | None = Field(None, alias="nameField")
    filter_types: list[str] | None = Field(None, alias="filterTypes")


class IgvReferenceGenome(IgvBase):
    """IGV reference genome container."""

    name: str
    fasta_url: str = Field(..., alias="fastaURL")
    index_url: str = Field(..., alias="indexURL")
    cytoband_url: str | None = Field(None, alias="cytobandURL")


class IgvConfig(IgvBase):
    """Definition of data used by IGV."""

    model_config = ConfigDict(
        populate_by_name=True,
        ser_json_exclude_none=True
    )

    locus: str
    reference: IgvReferenceGenome
    tracks: list[IgvTrack] = []
    # IGV configuration
    show_ideogram: bool = Field(False, alias="showIdeogram")
    show_svg_button: bool = Field(True, alias="showSVGButton")
    show_ruler: bool = Field(True, alias="showRuler")
    show_center_guide: bool = Field(False, alias="showCenterGuide")
    show_cursor_track_guide: bool = Field(False, alias="showCursorTrackGuide")
