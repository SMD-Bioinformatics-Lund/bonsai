"""Models used by pipeline builders."""

import hashlib
import json
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field, computed_field, model_validator



PipelineProjection: TypeAlias = dict[str, int | str]
PipelineStage: TypeAlias = dict[str, Any]
PipelineStages: TypeAlias = list[PipelineStage | PipelineProjection]
BuildOutput = Literal['tool', 'root', 'both']


class BuilderArgs(BaseModel):
    """Describe builder arguments."""

    selector: dict[str, str]
    source_path: str
    output: BuildOutput = "tool"
    label_field: str = "software"
    output_field: str | None = None
    exclude_fields: list[str] = []
    default_result: Any | None = None
    hit: int = Field(0, description="Index of default hit to select if multiple are present")


class LookupSpec(BaseModel):
    """Describe how to lookup information from other collections."""
    from_collection: str = Field(..., description="Name of the collection to join")
    as_field: str = Field(..., description="the output array field")
    let: dict[str, Any] | None = None
    pipeline: list[dict[str, Any]] = Field(default_factory=list)

    # Simple local/foreign equality join (works when localField is an array too)
    local_field: str | None = None
    foreign_field: str | None = None

    # Post-processing stages often used with lookups
    add_fields: dict[str, Any] | None = None     # e.g., {"groups_info": {"$map": ...}}
    project: dict[str, Any] | None = None        # e.g., {"groups_meta": 0}


ColumnType = Literal["string","number","integer","date","boolean","object"]


class ColumnBase(BaseModel):
    """User facing data."""

    id: str = Field(..., description="Column id")
    type: ColumnType = "string"
    label: str = Field(..., description="Display name")
    source: Literal["static", "metadata"] = (
        "static"  # where the columns are predefined or relate to metadata
    )
    default_visible: bool = False
    filterable: bool = True
    sortable: bool = True


class ColumnFull(ColumnBase):  # pylint: disable=too-few-public-methods
    """Internal data used for building pipeline queries."""

    path: Any = Field(..., description="Describing how to access the data in mongo object")
    requires: list[str] = []


class Manifest(BaseModel):
    """Internal backend manifest spec used for aggregation pipeline compilation."""
    columns: list[ColumnFull]
    filters: list[str] = []


    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [c.id for c in self.columns]
        if len(ids) != len(set(ids)):
            dups = {x for x in ids if ids.count(x) > 1}
            raise ValueError(f"Duplicate column ids: {sorted(dups)}")
        return self


    def _canonical_payload(self) -> bytes:
        """Produce a deterministic byte payload for hashing.
        Exclude computed fields and any non-deterministic values.
        Also sort structures to avoid incidental ordering differences.
        """
        # Dump without computed fields and canonicalize order
        d = self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude={"etag", "version"}
        )
        # Sort columns by id, filters by id, groups by id
        d["columns"] = sorted(d.get("columns", []), key=lambda x: x["id"])
        d["filters"] = sorted(d.get("filters", []), key=lambda x: x["id"])

        # dump manifest as stable hashable string
        payload = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return payload


    @computed_field(return_type=str)  # included in .model_dump() and OpenAPI
    def etag(self) -> str:
        """Compute ETag.
        
        Ref: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag
        """
        raw = self._canonical_payload()
        return f'W/"{hashlib.sha1(raw).hexdigest()}"'

    @computed_field(return_type=str)
    def version(self) -> str:
        """Compute human-readable version."""
        raw = self._canonical_payload()
        return hashlib.md5(raw).hexdigest()[:8]


class ManifestOutput(BaseModel):
    """Output version of manifest."""

    columns: list[ColumnBase]
    etag: str
    version: str

    @classmethod
    def from_internals(cls, spec: Manifest) -> "ManifestOutput":
        """Create a public version of the manifest."""

        pub_cols = [
            ColumnBase(
                id=col.id,
                label=col.label,
                source=col.source,
                type=col.type,
                default_visible=col.default_visible,
                filterable=col.filterable,
                sortable=col.sortable
            )
            for col in spec.columns
        ]
        return cls(
            columns=pub_cols,
            filters=spec.filters,
            etag=spec.etag,
            version=spec.version
        )