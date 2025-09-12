LIMS Export — Configuration & Usage
===================================

This guide explains how to **configure** and **use** the LIMS export feature in the Bonsai API,
covering both the **HTTP API** and the **CLI**.

.. contents::
   :local:
   :depth: 2


Overview
--------

The LIMS export produces a tabular file (TSV or CSV) composed of **rows** with the columns:

- ``sample_id``
- ``parameter_name``
- ``parameter_value``
- ``comment``

For a given ``sample_id``, the system looks up an **assay-specific configuration** and then,
for each configured field, calls a **formatter** by its ``data_type`` to compute the value and comment.

A **single field produces exactly one row**. The total number of rows equals the number
of fields in the matched ``AssayConfig``. If you want to export resistance to multiple antibiotics
or report motif that are expected to confere high or low level of resistance separately you have to 
have one field per antibiotic or resistance level.


Configuration Schema (YAML)
---------------------------

The export configuration is a **YAML list** of ``AssayConfig`` entries:

- ``assay: str`` — must match ``sample.pipeline.assay`` for the sample
- ``fields: list[FieldDefinition]`` — one entry per desired output row

**FieldDefinition:**

- ``parameter_name: str`` — the label that appears in the LIMS output
- ``data_type: str`` — the **registered** formatter name (see Built-in Formatters)
- ``required: bool`` — whether the **analysis must be present** on the sample
- ``options: dict`` — optional arguments passed to the formatter

Example
~~~~~~~

.. code-block:: yaml

    # lims_export.yaml

    - assay: "saureus"
      fields:
        - parameter_name: "Species (Bracken)"
          data_type: "species"
          required: true
          options:
            software: "bracken"             # default "bracken" | e.g. "mykrobe"
            sort_by: "fraction_total_reads" # default depends on software

        - parameter_name: "QC Status"
          data_type: "qc"
          required: true
          options: {}

        - parameter_name: "Lineage (TBProfiler)"
          data_type: "lineage"
          required: false
          options: {}

        - parameter_name: "MLST ST"
          data_type: "mlst"
          required: false
          options: {}

        - parameter_name: "Rifampicin resistance variants"
          data_type: "amr"
          required: false
          options:
            antibiotic_name: "rifampicin"
            software: "tbprofiler"          # default
            resistance_level: "all"         # include only motif with predicted resistance level, default: "all"

    - assay: "strep"
      fields:
        - parameter_name: "EMM Type"
          data_type: "emm"
          required: false
          options: {}

.. note::

   - **Assay names are case-sensitive** and must exactly match the database value in
     ``sample.pipeline.assay``.
   - For clarity in downstream systems, keep ``parameter_name`` values **unique** within an assay.


How the Export Works
--------------------

1. **Load and select config**:
   - The YAML is parsed into a list of ``AssayConfig``.
   - The system selects the config whose ``assay`` matches the sample’s ``pipeline.assay``.

2. **Per-field formatting**:
   - For each ``FieldDefinition`` in ``config.fields``:
     - Resolve the formatter with ``get_formatter(field.data_type)``.
     - Invoke it as ``formatter(sample, options=field.options)``.
     - The formatter returns a tuple: ``(value, comment)``.

3. **Error semantics (per field)**:
   - If the formatter raises:
     - ``AnalysisNotPresentError`` → treat as **not present**:
       - If ``required=True`` → **abort** the export by raising ``ValueError``.
       - If ``required=False`` → include a row with ``parameter_value = "-"`` (see below),
         ``comment = "not_present"``.
     - ``AnalysisNoResultError`` → analysis present but **no result**:
       - Include a row with ``parameter_value = "-"``, ``comment = "no_result"`` (even if required).
     - Any other exception → **propagate** (logged as unexpected error).
   - If the formatter returns a value of ``None`` or empty string, the system serializes it as ``"-"``.

4. **Row construction**:
   - Each field yields one ``LimsRsResult`` row with:
     - ``sample_id``: from the sample
     - ``parameter_name``: from the field
     - ``parameter_value``: passed through an internal sanitizer:
       - ``None`` or ``""`` → ``"-"``
       - otherwise → ``str(value)``
     - ``comment``: formatter comment or one of ``"not_present"`` / ``"no_result"``

5. **Serialization**:
   - ``serialize_lims_results(results, delimiter)`` writes a **header row** followed by data rows.
   - ``delimiter`` is a token: ``"csv"`` (`,`) or ``"tsv"`` (`\t`).


Built-in Formatters
-------------------

Formatters are registered by name using a decorator:

.. code-block:: python

   _FORMATTERS: dict[str, Formatter] = {}

   def register_formatter(name: str) -> Callable[[Formatter], Formatter]:
       ...

   @register_formatter("mlst")
   def mlst_typing(sample, *, options) -> tuple[LimsAtomic, LimsComment]: ...

The following formatter names are available by default:

- ``"species"`` — Species prediction.
  
  **Options**:
  - ``software``: ``"bracken"`` (default) or another supported tool name
  - ``sort_by``: for *bracken* default is ``"fraction_total_reads"``; for *mykrobe* default is ``"species_coverage"``

  **Behavior**:
  - Selects results for the chosen ``software``.
  - Sorts and returns the top hit’s scientific name.
  - If no predictions present → ``AnalysisNotPresentError``.
  - If predictions list is empty → ``AnalysisNoResultError``.

- ``"qc"`` — QC status.

  **Options**: none.

  **Behavior**:
  - Returns a capitalized QC classification (e.g., ``"Pass"`` / ``"Fail"``).

- ``"mlst"`` — MLST sequence type.

  **Options**: none.

  **Behavior**:
  - Returns the ``sequence_type`` or the literal ``"novel"`` when appropriate.
  - If MLST analysis missing → ``AnalysisNotPresentError``.
  - If analysis present with no value → ``AnalysisNoResultError``.

- ``"emm"`` — EMM type (Streptococcus).

  **Options**: none.

  **Behavior**:
  - Returns the EMM type or ``"novel"`` when appropriate.
  - Missing analysis → ``AnalysisNotPresentError``.

- ``"lineage"`` — Lineage (TBProfiler).

  **Options**: none.

  **Behavior**:
  - Returns a sublineage string (e.g., ``"2.2.1"``).

- ``"amr"`` — AMR prediction for a given antibiotic.

  **Options**:
  - ``antibiotic_name``: e.g., ``"rifampicin"`` (default)
  - ``software``: e.g., ``"tbprofiler"`` (default)
  - ``resistance_level``: ``"all"`` (default) or a specific level

  **Behavior**:
  - Returns a comma-separated list of resistance variants (genes currently **TODO**).
  - If no variants match → ``AnalysisNoResultError``.

.. note::

   You can add custom formatters by registering them with ``@register_formatter("<name>")``.
   In the YAML, set ``data_type: "<name>"`` for fields that should use your formatter.


API Usage
---------

Endpoint
~~~~~~~~

.. code-block:: http

   GET /export/{sample_id}/lims

**Output format**: The service typically serializes as **TSV** by default.
If your deployment supports a query switch (e.g., ``?fmt=csv|tsv``), use it to select the format.

Responses (typical)
~~~~~~~~~~~~~~~~~~~

- **200 OK**: Returns text body with **header row** and data rows.
- **404 Not Found**: No configuration exists for the sample’s assay, or the sample ID is missing (implementation-dependent).
- **500 Internal Server Error**:
  - Configuration parsing/formatting problems (e.g., invalid YAML, required analysis not present in a required field).
- **501 Not Implemented**: A field references a ``data_type`` with **no registered formatter**.

Example
~~~~~~~

.. code-block:: bash

   curl -H "Authorization: Bearer <token>" \
        -o sample123_lims.tsv \
        "https://api.example.com/export/sample123/lims"


CLI Usage
---------

Command
~~~~~~~

.. code-block:: console

   bonsai export --sample-id <ID> [--export-cnf PATH] [--format {csv,tsv}] [OUTPUT]

Options & arguments
~~~~~~~~~~~~~~~~~~~

- ``--sample-id, -i`` (**required**): The sample ID to export.
- ``--export-cnf, -e``: Path to the YAML configuration. If provided but missing, the CLI exits with an error.
- ``--format, -f``: ``csv`` or ``tsv``. Controls the **token** passed to the serializer.
- ``OUTPUT`` (positional): File to write. Defaults to ``-`` (stdout).

Behavior
~~~~~~~~

- Loads the configuration (`load_export_config`).
- Matches the sample’s ``pipeline.assay`` to an ``AssayConfig``.
- Builds rows via ``lims_rs_formatter(sample, config)``.
- Writes the table with:

  .. code-block:: python

     serialize_lims_results(lims_data, delimiter=output_format)  # output_format ∈ {"csv", "tsv"}

- If no configuration for the assay: prints a red error and aborts.
- If parsing/formatting errors occur (e.g., invalid YAML, required analysis missing):
  prints a yellow message and aborts.

Examples
~~~~~~~~

Write TSV to a file:

.. code-block:: bash

   bonsai export -i sample123 -f tsv results/sample123_lims.tsv

Write CSV to stdout and pipe:

.. code-block:: bash

   bonsai export -i sample123 -f csv - | column -s, -t

Use a specific config file:

.. code-block:: bash

   bonsai export -i sample123 -e /srv/bonsai/lims_export.yaml -f tsv sample123.tsv


Serialization Details
--------------------

- **Delimiter selection**: pass a **token**:
  - ``"csv"`` → comma (``","``)
  - ``"tsv"`` → tab (``"\t"``)
- **Header**: Always included with columns:
  ``sample_id, parameter_name, parameter_value, comment``.
- **Missing values**: Rendered as a single hyphen ``"-"``.
- **Quoting**: ``csv.QUOTE_MINIMAL``.
- **Encoding**: The function returns a Python ``str``. When writing to files or over HTTP,
  ensure **UTF-8** is used (typical default in modern deployments).


Error Semantics (Summary)
-------------------------

Per field (inside ``lims_rs_formatter``):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``AnalysisNotPresentError``:
  - If field ``required=True`` → abort whole export.
  - If field ``required=False`` → include row with ``parameter_value="-"``, ``comment="not_present"``.
- ``AnalysisNoResultError``:
  - Include row with ``parameter_value="-"``, ``comment="no_result"`` (does **not** abort).
- Any other exception:
  - Logged and re-raised.

At the integration layer:
~~~~~~~~~~~~~~~~~~~~~~~~~

- **CLI**: shows colored messages and aborts on errors (e.g., config not found, invalid YAML, ValueError).
- **API**: typically maps:
  - Missing config for assay → **404**
  - Unimplemented formatter → **501**
  - Invalid format / missing required analysis (ValueError) / unreadable config → **500**


Extending the System
--------------------

Register a new formatter
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from bonsai_api.lims_export.models import LimsAtomic, LimsComment
   from bonsai_api.lims_export.formatters import register_formatter, AnalysisNotPresentError, AnalysisNoResultError

   @register_formatter("my_custom_type")
   def my_custom_formatter(sample, *, options=None) -> tuple[LimsAtomic, LimsComment]:
       # Inspect sample; raise AnalysisNotPresentError if analysis not attached
       # Raise AnalysisNoResultError if analysis attached but no data
       # Otherwise return (value, optional_comment)
       value = "some-derived-value"
       comment = ""
       return value, comment

Then, reference the formatter in YAML:

.. code-block:: yaml

   - assay: "example-assay"
     fields:
       - parameter_name: "My Custom Field"
         data_type: "my_custom_type"
         required: false
         options:
           threshold: 0.9


Best Practices
--------------

- Keep the YAML under **version control**; validate changes in CI.
- Ensure **assay names** match DB values exactly.
- Prefer **unique** ``parameter_name`` values per assay to avoid confusion downstream.
- Use ``required=True`` sparingly—only for truly mandatory analyses.
- For user-facing consistency, reserve ``comment`` values for:
  - ``"not_present"`` (analysis missing)
  - ``"no_result"`` (present but empty)
  - Additional comments from formatters as needed.
- When targeting Excel ingestion, prefer **CSV**; for robust pipelines, prefer **TSV**.
