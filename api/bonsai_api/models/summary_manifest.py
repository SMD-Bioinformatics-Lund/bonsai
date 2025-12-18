"""Definitions of samples summaries"""

import hashlib
import json
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field, computed_field, model_validator


BuildOutput = Literal['tool', 'root', 'both']
PipelineStages: TypeAlias = list[dict[str, Any]]
PipelineProjection: TypeAlias = dict[str, int | str]



class BuilderArgs(BaseModel):
    """Describe builder arguments."""

    selector: dict[str, str]
    source_path: str
    output: BuildOutput = "tool"
    label_field: str = "software"
    output_field: str | None = None
    exclude_fields: list[str] = []
    

class SummaryBuildEntry(BaseModel):
    """Describe how to summize data in the summary."""

    name: str
    args: BuilderArgs
    projection: bool | str | int = True


class SummaryConfig(BaseModel):
    """Configure how to summarize sample info"""

    builders: list[SummaryBuildEntry]
    emit: list[dict[str, str | int | dict[str, str]]] = Field([], description="Whitelist fields")
    drop_after_build: list[str] = Field([], description="Prevent these fields from being returned")
    hide: list[str] = Field(default=["_id"], description="Allways hide these fields")


ColumnType = Literal["string","number","integer","date","boolean","object"]


class ColumnBase(BaseModel):
    id: str = Field(..., description="Column id")
    type: ColumnType = "string"
    label: str = Field(..., description="Display name")
    source: Literal["static", "metadata"] = (
        "static"  # where the columns are predefined or relate to metadata
    )
    default_visible: bool | None = None
    filterable: bool = True
    sortable: bool = True


class ColumnFull(ColumnBase):  # pylint: disable=too-few-public-methods
    """Definition of valid columns for sample summary."""

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
    filters: list[str]
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