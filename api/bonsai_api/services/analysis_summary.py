"""Populate the SDK's STX display field on existing sample results."""

from bonsai_libs.parse.models.typing import TypingResultStx


async def backfill_typing_summaries(db, *, dry_run: bool = False) -> dict[str, int]:
    """Add the STX display field without replacing hits or concurrent changes."""
    counts = {"pending": 0, "updated": 0, "conflicts": 0}
    cursor = db.sample_collection.find(
        {"typing_result.software": "virulencefinder"},
        {"typing_result": 1},
    )
    async for sample in cursor:
        source = sample.get("typing_result") or []
        entries = (
            [("typing_result", source)]
            if isinstance(source, dict)
            else [(f"typing_result.{i}", entry) for i, entry in enumerate(source)]
        )
        for path, entry in entries:
            if (
                entry.get("software") != "virulencefinder"
                or entry.get("analysis_type") != "stx"
                or entry.get("status", "parsed") != "parsed"
            ):
                continue
            result = entry.get("result")
            if not result:
                continue
            payload = {"hits": result} if isinstance(result, list) else result
            if not payload.get("hits"):
                continue  # Older single-gene results already have gene_symbol.
            model = TypingResultStx.model_validate(payload)
            prepared = {**payload, "gene_symbol": model.gene_symbol}
            if prepared == result:
                continue
            counts["pending"] += 1
            if not dry_run:
                outcome = await db.sample_collection.update_one(
                    {"_id": sample["_id"], path: entry},
                    {"$set": {f"{path}.result": prepared}},
                )
                counts["updated" if outcome.matched_count else "conflicts"] += 1
    return counts
