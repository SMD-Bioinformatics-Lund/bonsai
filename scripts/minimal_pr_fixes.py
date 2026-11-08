"""Issue-scoped production edits for the local release-fix branches.

Each edit starts at the development baseline or an explicitly named prerequisite.
Previously verified changes are transferred by hunk, without unrelated changes
from the combined test branch. No live service or database is used here.
"""

import ast
import re
import subprocess


class Edits:
    def __init__(self, repo, base):
        self.repo, self.base, self.files = repo, base, {}

    def read(self, path):
        if path not in self.files:
            self.files[path] = subprocess.check_output(['git', '-C', str(self.repo), 'show', f'{self.base}:{path}'], text=True)
        return self.files[path]

    def replace(self, path, before, after, count=1):
        text = self.read(path)
        if text.count(before) != count:
            raise ValueError(f'Expected {count} occurrences in {path}: {before!r}; found {text.count(before)}')
        self.files[path] = text.replace(before, after)

    def transfer(self, commit, path, select=None, macro=None):
        diff = subprocess.check_output(['git', '-C', str(self.repo), 'diff', f'{commit}^', commit, '--', path], text=True)
        hunks = re.split(r'(?=^@@ )', diff, flags=re.M)[1:]
        if not hunks:
            raise ValueError(f'No saved patch for {commit}: {path}')
        chosen = [h for h in hunks if select is None or select(h)]
        if not chosen:
            raise ValueError(f'No matching hunk for {commit}: {path}')
        for hunk in chosen:
            lines = hunk.splitlines()[1:]
            before = '\n'.join(line[1:] for line in lines if line.startswith((' ', '-'))) + '\n'
            after = '\n'.join(line[1:] for line in lines if line.startswith((' ', '+'))) + '\n'
            if macro and self.read(path).count(before) > 1:
                text = self.read(path)
                start = text.index('{% macro ' + macro + '(')
                end = text.index('{% endmacro %}', start) + len('{% endmacro %}')
                region = text[start:end] + '\n'
                if region.count(before) != 1:
                    raise ValueError(f'Macro patch is ambiguous: {path} / {macro}')
                self.files[path] = text[:start] + region.replace(before, after).removesuffix('\n') + text[end:]
            else:
                self.replace(path, before, after)

    def function(self, path, name, replacement):
        text = self.read(path)
        nodes = [n for n in ast.walk(ast.parse(text)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
        if len(nodes) != 1:
            raise ValueError(f'Expected one function {path}: {name}')
        old = ast.get_source_segment(text, nodes[0])
        self.replace(path, old, replacement.rstrip())


def apply(issue, edit):
    api = 'api/bonsai_api/'
    front = 'frontend/bonsai_app/'
    js = 'frontend/web/js/'
    controllers = front + 'blueprints/sample/controllers.py'
    sample_view = front + 'blueprints/sample/views.py'
    sample_html = front + 'blueprints/sample/templates/sample.html'
    cards = front + 'blueprints/sample/templates/cards.html'
    metadata = api + 'crud/metadata.py'
    if issue == 'ORDINARY-RECORD-DELETE':
        path = api + 'routers/samples/samples.py'
        text = edit.read(path)
        for name in ['delete_many_samples', 'delete_sample']:
            node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            old = ast.get_source_segment(text, node)
            edit.replace(path, old, old.replace('scopes=[UPDATE_PERMISSION]', 'scopes=[WRITE_PERMISSION]'))
    elif issue == 'ACCOUNT-ROLE-PERMISSIONS':
        edit.transfer('3caa9134', api + 'dependencies.py')
        edit.transfer('3caa9134', api + 'routers/analysis.py')
        edit.transfer('3caa9134', api + 'routers/samples/samples.py', lambda h: 'async def list_samples' in h)
    elif issue == 'ANALYSIS-UPLOAD-ROLE-GATE':
        path = api + 'routers/analysis.py'
        text = edit.read(path)
        node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'upload_analysis')
        old = ast.get_source_segment(text, node)
        edit.replace(path, old, old.replace('scopes=["users:me"]', 'scopes=[WRITE_PERMISSION]'))
    elif issue == 'PRIVATE-RECORD-SCOPE':
        path = api + 'models/sample.py'
        text = edit.read(path)
        node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.ClassDef) and n.name == 'SampleInfoCreate')
        old = ast.get_source_segment(text, node)
        edit.replace(path, old, old.replace('visibility: Visibility = Visibility.PUBLIC', 'visibility: Literal[Visibility.PUBLIC] = Visibility.PUBLIC'))
        if 'from typing import Literal' not in edit.read(path) and 'from typing import Any, Literal' not in edit.read(path):
            edit.replace(path, 'from typing import Any', 'from typing import Any, Literal')
    elif issue == 'GROUP-DELETE-MEMBERSHIP-LOSS':
        edit.transfer('d64667d7', api + 'crud/memberships.py')
    elif issue == 'GROUP-MEMBERSHIP-LOSS':
        path = js + 'components/group-selector.ts'
        edit.replace(path, '  private currentMemberships: MembershipBySample = {};', '  private currentMemberships: MembershipBySample = {};\n  private commonGroupIds = new Set<string>();')
        edit.replace(path, '    const selectedGroupIds: string[] = this.selector.getSelected();', '    const selectedGroupIds: string[] = this.selector.getSelected();\n    const memberships = this.currentMemberships;\n    const commonGroupIds = new Set(this.commonGroupIds);')
        edit.replace(path, 'const currentGroups = new Set(this.currentMemberships[sampleId] ?? []);', 'const currentGroups = new Set(memberships[sampleId] ?? []);')
        edit.replace(path, 'const toRemove = [...currentGroups].filter(gid => !targetGroups.has(gid));', 'const toRemove = [...commonGroupIds].filter(gid => currentGroups.has(gid) && !targetGroups.has(gid));')
        edit.replace(path, '      this.selector.setSelected(groupNameIntersect);', '      this.commonGroupIds = new Set(groupNameIntersect);\n      this.selector.setSelected(groupNameIntersect);')
        edit.replace(path, '      if (membershipChanged) {\n        emitEvent("samples:group-memberships-changed", { sampleIds });\n      }', '      if (membershipChanged) {\n        emitEvent("samples:group-memberships-changed", { sampleIds });\n        await this.preselectGroupsForSamples(this.currentSelectedSamples);\n      }')
    elif issue == 'GROUP-MEMBERSHIP-LIMIT':
        edit.transfer('d64667d7', js + 'core/api/index.ts')
    elif issue == 'METADATA-ADD-500':
        edit.replace(metadata, 'db_fieldnames = {meta.fieldname for meta in sample_meta}', 'db_fieldnames = {meta["fieldname"] for meta in sample_meta}')
        edit.replace(metadata, "{metadata.fieldname}", "{input_fieldnames}")
        edit.replace(metadata, 'meta_info: list[MetaEntryInDb] = []', 'meta_info: list[dict[str, Any]] = []')
        edit.replace(metadata, 'meta_info.append(parse_metadata_table(entry=record))', 'meta_info.append(parse_metadata_table(entry=record).model_dump())')
        edit.replace(metadata, 'meta_info.append(record)', 'meta_info.append(record.model_dump())')
        edit.replace(metadata, '[meta.model_dump() for meta in meta_info]', 'meta_info')
    elif issue == 'RECOVERY-METADATA-LOSS':
        edit.replace(metadata, "    for meta in sample_meta:\n        if meta['fieldname'] not in input_fieldnames:\n            meta_info.append(meta)\n", '')
        edit.replace(metadata, '{"sample_id": sample_id},\n        {"$set": {"metadata": meta_info}},', '{"sample_id": sample_id, "metadata.fieldname": {"$nin": list(input_fieldnames)}},\n        {"$push": {"metadata": {"$each": meta_info}}},')
        edit.replace(metadata, '    if cursor.matched_count == 0:\n        raise EntryNotFound(sample_id)', '    if cursor.matched_count == 0:\n        if await get_sample_by_id(db, sample_id=sample_id) is None:\n            raise EntryNotFound(sample_id)\n        raise FileExistsError("A metadata field was added by another request")')
    elif issue == 'METADATA-CATEGORY-LOSS':
        edit.replace(controllers, 'groupby(metadata, key=lambda x: x["category"])', 'groupby(sorted(metadata, key=lambda x: x["category"]), key=lambda x: x["category"])')
    elif issue == 'METADATA-TABLE-EMPTY':
        for path in [api + 'models/metadata.py', api + 'models/sample.py', front + 'blueprints/sample/templates/metadata.html']:
            edit.transfer('d64667d7', path)
    elif issue == 'CSV-EMPTY-CELL-500':
        path = api + 'models/metadata.py'
        edit.replace(path, 'from datetime import datetime', 'from datetime import datetime\nimport math')
        edit.replace(path, 'from pydantic import BaseModel', 'from pydantic import BaseModel, field_validator')
        marker = '\n\nInputMetaEntry ='
        method = '\n    @field_validator("data", mode="before")\n    @classmethod\n    def normalize_empty_cells(cls, rows):\n        return [["" if isinstance(cell, float) and math.isnan(cell) else cell for cell in row] for row in rows]\n'
        edit.replace(path, marker, method + marker)
    elif issue == 'ADMIN-CREATE-USER-500':
        path = front + 'blueprints/admin/views.py'
        edit.replace(path, 'from requests.exceptions import HTTPError', 'from requests.exceptions import HTTPError\nfrom bonsai_libs.api_client.core.exceptions import NotFoundError')
        edit.replace(path, '        except HTTPError as error:\n            if error.response.status_code == 404:\n                user_exists = False\n            else:\n                raise error', '        except NotFoundError:\n            user_exists = False')
    elif issue == 'ADMIN-EDIT-USER-500':
        edit.transfer('d64667d7', front + 'blueprints/admin/views.py', lambda h: 'elif request.method == "GET"' in h)
        edit.transfer('d64667d7', api + 'crud/user.py')
    elif issue == 'PRIVATE-GROUP-INVITE-500':
        for path in [api + 'services/group_service.py', api + 'crud/group.py']:
            edit.transfer('d64667d7', path)
    elif issue == 'QC-FILTER-EMPTY':
        edit.transfer('d64667d7', js + 'views/groups-view/init.ts')
        edit.transfer('d64667d7', front + 'blueprints/groups/templates/cell_fmt.html')
    elif issue == 'PENDING-SAMPLE-500':
        edit.transfer('d64667d7', cards, lambda h: 'sample_info.pipeline.pipeline_info.databases' in h)
        edit.transfer('d64667d7', cards, lambda h: 'sample_info.pipeline.pipeline_info.databases' not in h, macro='analysis_meta_pipeline')
        edit.transfer('d64667d7', sample_view)
    elif issue == 'TB-CURATION-500':
        edit.transfer('e11cecf8', cards)
    elif issue == 'TB-NO-AMR-500':
        edit.transfer('e11cecf8', controllers)
        edit.transfer('e11cecf8', sample_html)
        edit.replace(controllers, 'variants = prediction["result"]["variants"]', 'variants = (prediction.get("result") or {}).get("variants", [])', count=3)
        edit.replace(controllers, 'for variant in prediction["result"]["variants"]', 'for variant in (prediction.get("result") or {}).get("variants", [])')
        if 'if not analysis_result.get("result")' not in edit.read(controllers):
            edit.replace(controllers, 'if "result" not in analysis_result or "variants" not in analysis_result["result"]:', 'if not analysis_result.get("result") or "variants" not in analysis_result["result"]:')
        edit.replace(sample_view, '    for pred_res in tbprofiler_results:\n        pred_res["result"]["variants"]', '    for pred_res in tbprofiler_results:\n        if pred_res.get("result") is None:\n            continue\n        pred_res["result"]["variants"]')
        edit.replace(sample_view, 'if "variants" in pred_res.get("result", {}):', 'if "variants" in (pred_res.get("result") or {}):')
        path = front + 'blueprints/sample/templates/resistance_variants.html'
        edit.replace(path, '            <div id="phenotype-heading"', '            {% if amr_results and not (amr_results | selectattr("result") | list) %}\n                <p>Stored variant detail results are unavailable for this record.</p>\n            {% endif %}\n            <div id="phenotype-heading"')
    elif issue == 'VARIANT-FILTER-AND':
        edit.replace(controllers, 'variant_passes_qc = variant["depth"] >= int(min_depth)', 'variant_passes_qc = variant_passes_qc and variant["depth"] >= int(min_depth)')
        edit.replace(controllers, 'variant_passes_qc = variant["depth"] <= int(min_depth)', 'variant_passes_qc = variant_passes_qc and variant["depth"] <= int(min_depth)')
    elif issue == 'VARIANT-HIDE-DISMISSED-500':
        edit.replace(controllers, 'if bool(form.get("hide-dismissed")) and variant["verified"] == "failed":', 'if bool(form.get("hide-dismissed")) and (variant.get("curation") or {}).get("decision") == "reject":')
        edit.replace(controllers, '    for prediction in sample_info["element_type_result"]:\n        variants = prediction["result"]["variants"]', '    for prediction in sample_info["element_type_result"]:\n        merge_variants_with_curations(prediction)\n        variants = prediction["result"]["variants"]')
    elif issue == 'ECOLI-VARIANTS-EMPTY':
        path = front + 'blueprints/sample/templates/resistance_variants.html'
        edit.replace(path, 'No predicted resistance to validated phenotypes. Use the extended resistance report to see all predicted resistance.', 'No stored TBProfiler variant result is displayed with these filters. Use the extended report to inspect the available stored results.')
        edit.replace(path, 'No predicted resistance determinants.', 'No stored TBProfiler variant result is available in this view. Other stored result types are not displayed here.')
    elif issue == 'DISPLAY-EMM-TABLE':
        edit.transfer('9ecd142b', api + 'crud/builder/summary_manifest.py')
    elif issue == 'DISPLAY-EXTENDED-CONTEXT':
        edit.transfer('9ecd142b', sample_html, lambda h: 'from "cards.html"' in h)
    elif issue == 'EMM-DISPLAY-MISSING':
        edit.transfer('9ecd142b', cards, lambda h: 'base_url' not in h, macro='emm_card')
        edit.transfer('9ecd142b', sample_html, lambda h: 'res.analysis_type' in h)
        edit.replace(sample_html, 'res.analysis_type in ["emm", "emmtype"]', 'res.analysis_type == "emm"')
    elif issue == 'EMM-LIMS-EXPORT-500':
        edit.transfer('84e94d71', api + 'lims_export/formatters.py')
    elif issue == 'ACCOUNT-STALE-PAGES':
        path = front + 'templates/bootstrap_base.html'
        old = edit.read(path)
        patch = subprocess.check_output(['git', '-C', str(edit.repo), 'show', '3caa9134:' + path], text=True)
        block = patch.split('        <script>\n        // Keep rendered account state', 1)[1].split('        </script>', 1)[0]
        block = '        <script>\n        // Keep rendered account state' + block + '        </script>\n'
        block = block.replace('            try {\n', '').replace('            } catch (_) { /* Storage can be unavailable in restricted browser profiles. */ }\n', '')
        edit.replace(path, '    </head>', block + '    </head>')
    elif issue == 'BASKET-UNDEFINED-ASSAY':
        path = js + 'components/sample-basket.ts'
        helper = '\nconst htmlEscapes: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", \'"\': "&quot;", "\'": "&#39;" };\nfunction escapeHtml(value: unknown): string {\n  return String(value).replace(/[&<>"\']/g, character => htmlEscapes[character]);\n}\n'
        edit.replace(path, '\nexport class BasketComponent', helper + '\nexport class BasketComponent')
        edit.replace(path, '${sample.sample_name}', '${escapeHtml(sample.sample_name)}')
        edit.replace(path, '${sample.assay}', '${sample.assay ?? ""}')
    elif issue == 'CURATION-DOUBLE-SUBMIT':
        edit.replace(controllers, '        resp = create_curation_fn(\n            analysis_type=analysis_type,\n            analysis_id=analysis_id,\n            record=curation_record,\n        )\n        try:', '        try:')
        edit.replace(sample_view, '                results = submit_curations_batch(batch_records, create_curation_fn=client.create_curation)', '                results = submit_curations_batch(batch_records, create_curation_fn=client.create_curation)\n                sample_info = client.get_sample_by_id(sample_id=sample_id)')
    elif issue == 'VARIANT-SELECT-ALL-INVALID':
        path = js + 'views/variants-table/variants-view.ts'
        edit.replace(path, '".br-content input[type=\'checkbox\']"', '".br-content input[type=\'checkbox\'][data-variant-id]"')
        edit.replace(path, '"input[type=\'checkbox\']"', '"input[type=\'checkbox\'][data-variant-id]"')
    elif issue == 'SELECTED-FILTER-STALE':
        path = js + 'utils/table-controller.ts'
        edit.replace(path, '  const controller = new TableController(tableId, tableConfig);', '  const controller = new TableController(tableId, tableConfig);\n  controller.getTable().on("select deselect", () => controller.getTable().draw(false));')
    elif issue == 'RECOVERY-GROUP-OVERLAP':
        group_overlap(edit, js)
    elif issue == 'RECOVERY-COMMENT-IDENTITIES':
        comment_identifiers(edit, api)
    elif issue == 'RECOVERY-COMMENT-RETRY':
        comment_retry(edit, api, front)
    elif issue in ['KLEBORATE-UPLOAD-422', 'KLEBORATE-CLIENT-COMPANION']:
        kleborate_companion(edit, issue, api)
    elif issue in ['PARSER-MYKROBE-SELECTION', 'PARSER-BRACKEN-EMPTY', 'PARSER-COVERAGE-STREAM']:
        name = {'PARSER-MYKROBE-SELECTION': 'mykrobe', 'PARSER-BRACKEN-EMPTY': 'bracken', 'PARSER-COVERAGE-STREAM': 'samtools'}[issue]
        edit.transfer('ecf07a8', f'src/bonsai_libs/parse/parsers/{name}.py')
    else:
        raise ValueError('Missing issue-specific edit: ' + issue)


def group_overlap(edit, js):
    path = js + 'views/group-editor/index.ts'
    edit.replace(path, '  private isInitialized = false;', '  private isInitialized = false;\n  private savedCore = { display_name: "", description: "" };\n  private savedColumns: string[] = [];')
    edit.replace(path, '    this.model.loadFromApi(data);', '    this.model.loadFromApi(data);\n    this.savedCore = { display_name: data.display_name, description: data.description };\n    this.savedColumns = [...data.table_columns];')
    edit.replace(path, '      if ( this.mode == "create" ) {', '      const creating = this.mode === "create";\n      if ( this.mode == "create" ) {')
    edit.replace(path, '        await this._api.updateGroup(groupId, corePayload)', '        const changes: Partial<typeof corePayload> = {};\n        if (corePayload.display_name !== this.savedCore.display_name) changes.display_name = corePayload.display_name;\n        if (corePayload.description !== this.savedCore.description) changes.description = corePayload.description;\n        if (Object.keys(changes).length) await this._api.updateGroup(groupId, changes);')
    edit.replace(path, '      await this._api.updateAllowedColumns(\n        groupId,\n        selector.items.filter(item => item.enabled).map(item => item.id)\n      );', '      const columns = selector.items.filter(item => item.enabled).map(item => item.id);\n      if (creating || JSON.stringify(columns) !== JSON.stringify(this.savedColumns)) {\n        await this._api.updateAllowedColumns(groupId, columns);\n      }\n      this.savedCore = { ...corePayload };\n      this.savedColumns = [...columns];')
    for filename in ['views/group-editor/api.ts', 'core/api/services/groups.ts']:
        text = edit.read(js + filename)
        if 'data: InputCoreGroupInfo' not in text:
            raise ValueError('Missing group update input type')
        # Only updateGroup accepts a partial object. Creation remains a full input.
        if filename.endswith('api.ts'):
            edit.replace(js + filename, '    data: InputCoreGroupInfo', '    data: Partial<InputCoreGroupInfo>')
        else:
            edit.replace(js + filename, 'updateGroup(groupId: string, data: InputCoreGroupInfo)', 'updateGroup(groupId: string, data: Partial<InputCoreGroupInfo>)')


def comment_identifiers(edit, api):
    path = api + 'crud/sample.py'
    text = edit.read(path)
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'add_comment')
    old = ast.get_source_segment(text, node)
    # Keep the existing read/append contract; retry only an ID collision at the
    # conditional atomic append. No request-key behavior is added in this PR.
    signature = old.split('    # get existing comments', 1)[0]
    body = '''    event_subject = Subject(id=sample_id, type=SourceType.USR)
    meta = {"sample_id": sample_id}
    with audit_event_context(audit, "create_comment", ctx, event_subject, meta):
        while True:
            sample = await get_sample_by_id(db, sample_id=sample_id)
            comments = [CommentInDatabase.model_validate(c) for c in sample["comments"]]
            comment_id = max((c.id for c in comments), default=0) + 1
            meta["comment_id"] = comment_id
            comment_obj = CommentInDatabase(id=comment_id, **comment.model_dump())
            update_obj = await db.sample_collection.update_one(
                {"sample_id": sample_id, "comments.id": {"$ne": comment_id}},
                {"$set": {"modified_at": get_timestamp()},
                 "$push": {"comments": {"$each": [comment_obj.model_dump(by_alias=False)], "$position": 0}}},
            )
            if update_obj.matched_count:
                break
        if update_obj.modified_count != 1:
            raise DatabaseOperationError(sample_id)
        LOG.info("Added comment to %s", sample_id)
        comments.insert(0, comment_obj)
    return comments'''
    edit.replace(path, old, signature + body)


def comment_retry(edit, api, front):
    path = api + 'crud/sample.py'
    edit.replace(path, 'import logging', 'import logging\nfrom hashlib import sha256')
    text = edit.read(path)
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'add_comment')
    before = ast.get_source_segment(text, node)
    after = before.replace('    audit: AuditLogClient | None = None,\n)', '    audit: AuditLogClient | None = None,\n    *, request_key: str | None = None,\n)')
    after = after.replace('    event_subject =', '    key = sha256(f"{ctx.actor.id}\\0{request_key}".encode()).hexdigest() if request_key else None\n    event_subject =', 1)
    after = after.replace('            comment_id =', '''            if key:
                previous = next((c for c in sample["comments"] if c.get("_request_key") == key), None)
                if previous is not None:
                    if any(previous.get(k) != v for k, v in comment.model_dump(exclude={"created_at"}).items()):
                        raise ConflictError("Comment request key was already used with different content")
                    return comments
            comment_id =''', 1)
    after = after.replace('            update_obj =', '''            entry = comment_obj.model_dump(by_alias=False)
            query = {"sample_id": sample_id, "comments.id": {"$ne": comment_id}}
            if key:
                entry["_request_key"] = key
                query["comments._request_key"] = {"$ne": key}
            update_obj =''', 1)
    after = after.replace('{"sample_id": sample_id, "comments.id": {"$ne": comment_id}},\n', 'query,\n')
    after = after.replace('[comment_obj.model_dump(by_alias=False)]', '[entry]')
    edit.replace(path, before, after)
    path = api + 'routers/samples/sample_metadata.py'
    if 'from fastapi import (\n' in edit.read(path):
        edit.replace(path, 'from fastapi import (\n', 'from fastapi import (\n    Header,\n')
    else:
        edit.replace(path, 'from fastapi import ', 'from fastapi import Header, ')
    text = edit.read(path)
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'post_comment')
    before = ast.get_source_segment(text, node)
    after = before.replace('    db: Database = Depends(get_database),', '    request_key: str | None = Header(None, alias="Idempotency-Key"),\n    db: Database = Depends(get_database),')
    # Header wiring follows the existing service call; the CRUD already scopes it
    # to the authenticated actor and keeps it out of the public comment model.
    if 'audit=audit_log' in after:
        after = after.replace('audit=audit_log', 'audit=audit_log, request_key=request_key')
    elif 'ctx=req_ctx' in after:
        after = after.replace('ctx=req_ctx', 'ctx=req_ctx, request_key=request_key')
    elif 'add_comment(db, sample_id, comment, req_ctx, audit_log)' in after:
        after = after.replace('add_comment(db, sample_id, comment, req_ctx, audit_log)', 'add_comment(db, sample_id, comment, req_ctx, audit_log, request_key=request_key)')
    else:
        raise ValueError('The comment endpoint did not pass its request key')
    edit.replace(path, before, after)
    path = front + 'blueprints/sample/views.py'
    edit.replace(path, 'import logging', 'import logging\nfrom uuid import uuid4')
    edit.replace(path, 'from flask import (', 'from flask import (\n    g,')
    edit.replace(path, 'from requests import HTTPError', 'from requests import HTTPError, RequestException')
    imports = [node for node in ast.walk(ast.parse(edit.read(path))) if isinstance(node, ast.ImportFrom) and node.module == 'bonsai_libs.api_client.core.exceptions']
    if not any(name.name == 'ApiError' for node in imports for name in node.names):
        edit.replace(path, 'from uuid import uuid4', 'from uuid import uuid4\nfrom bonsai_libs.api_client.core.exceptions import ApiError')
    marker = '\n\n@samples_bp.route('
    text = edit.read(path);first = text.index(marker)
    hook = '''

@samples_bp.before_request
def identify_comment_submission():
    g.comment_request_key = request.form.get("comment_request_key") or str(uuid4())
'''
    edit.files[path] = text[:first] + hook + text[first:]
    text = edit.read(path)
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == 'add_comment')
    before = ast.get_source_segment(text, node)
    # The existing route supplies the username from the authenticated session.
    after = '''def add_comment(sample_id: str):
    client = get_api_client()
    comment = request.form["comment"]
    request_key = g.comment_request_key
    try:
        client.post_comment_to_sample(sample_id=sample_id, username=current_user.username, comment=comment,
                                      headers={"Idempotency-Key": request_key})
    except (ApiError, RequestException) as error:
        LOG.warning("Comment save could not be confirmed: %s", error)
        return render_template("comment_retry.html", sample_id=sample_id, comment=comment,
                               request_key=request_key), 503
    return redirect(url_for("samples.sample", sample_id=sample_id))'''
    edit.replace(path, before, after)
    path = front + 'blueprints/sample/templates/sidebar.html'
    edit.replace(path, '<form class="pb-2"\n      action={{ url_for(\'samples.add_comment\', sample_id=sample.sample_id) }} method="post">', '<form class="pb-2"\n      action={{ url_for(\'samples.add_comment\', sample_id=sample.sample_id) }} method="post">\n    <input type="hidden" name="comment_request_key" value="{{ g.comment_request_key }}">')
    edit.files[front + 'blueprints/sample/templates/comment_retry.html'] = '''{% extends "layout.html" %}
{% block content %}
<div class="container py-3">
    <p>The comment save could not be confirmed. It may already have been saved. Retrying this submission will not create a duplicate.</p>
    <form action="{{ url_for('samples.add_comment', sample_id=sample_id) }}" method="post">
        <input type="hidden" name="comment_request_key" value="{{ request_key }}">
        <textarea class="form-control" name="comment" required>{{ comment }}</textarea>
        <button class="btn btn-outline-success mt-2" type="submit">Retry comment</button>
    </form>
</div>
{% endblock %}
'''


def kleborate_companion(edit, issue, api):
    if issue == 'KLEBORATE-CLIENT-COMPANION':
        edit.replace('src/bonsai_libs/api_client/bonsai/models.py', '    bedcov_file: Path | None = None', '    bedcov_file: Path | None = None\n    hamronization_file: Path | None = None')
        edit.replace('src/bonsai_libs/api_client/bonsai/samples.py', '{"file", "coverage_file", "bedcov_file"}', '{"file", "coverage_file", "bedcov_file", "hamronization_file"}')
        edit.replace('src/bonsai_libs/api_client/bonsai/samples.py', '("coverage_file", "bedcov_file")', '("coverage_file", "bedcov_file", "hamronization_file")')
    else:
        path = api + 'routers/analysis.py'
        text = edit.read(path)
        node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'upload_analysis')
        old = ast.get_source_segment(text, node)
        edit.replace(path, old, old.replace('    db: Database = Depends(get_database),', '    hamronization_file: UploadFile | None = File(None, description="Optional hAMRonization companion output"),\n    db: Database = Depends(get_database),'))
        edit.replace(path, '        bedcov_file=bedcov_file,', '        bedcov_file=bedcov_file,\n        hamronization_file=hamronization_file,')
        path = api + 'services/analysis_service.py'
        edit.replace(path, '    bedcov_file: UploadFile | None = None,', '    bedcov_file: UploadFile | None = None,\n    hamronization_file: UploadFile | None = None,')
        edit.replace(path, '        parser_args: dict[str, Any] = {', '        if hamronization_file is not None:\n            auxiliary_files["hamronization_source"] = io.TextIOWrapper(hamronization_file.file, encoding="utf-8")\n        parser_args: dict[str, Any] = {')
