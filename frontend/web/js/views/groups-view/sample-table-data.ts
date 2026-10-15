import type { Config } from "datatables.net-bs5";
import type {
  ApiSampleQcStatus,
  SummaryColumn,
  SummaryComment,
  SummaryGroup,
  SummaryRow,
  SummaryTag,
} from "../../core/types";

interface OverviewData {
  columns: SummaryColumn[];
  rows: SummaryRow[];
}

export function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char],
  );
}

function text(value: unknown): string {
  if (value == null) return "";
  if (Array.isArray(value)) return value.map(text).join(", ");
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function tooltip(content: string, html = false): string {
  return `data-bs-toggle="tooltip" data-bs-placement="top" ${html ? 'data-bs-html="true"' : ""} data-bs-title="${escapeHtml(content)}"`;
}

// Non-display values stay plain text/numbers for sorting, filtering and export.
// Only the rows DataTables displays need presentation markup and DOM nodes.
export function renderSummaryCell(
  column: Pick<SummaryColumn, "renderer">,
  value: unknown,
  type: string,
  sampleUrl: string,
): string | number {
  const display = type === "display";
  if (column.renderer === "sample_btn_renderer") {
    return display
      ? `<a href="${escapeHtml(sampleUrl.replace("__sample_id__", encodeURIComponent(text(value))))}">Open</a>`
      : text(value);
  }
  if (column.renderer === "qc_status_renderer") {
    const qc = value as ApiSampleQcStatus | null;
    const status = qc?.status ?? "";
    if (!display) return status;
    const color = status === "passed" ? "text-success" : status === "failed" ? "text-danger" : "";
    const hint =
      qc?.action && qc?.comment
        ? `Action: ${qc.action} - ${qc.comment}`
        : qc?.action || qc?.comment;
    return (
      `<span class="fw-light ${color}">${escapeHtml(status)}</span>` +
      (hint ? ` <i class="bi bi-info-circle" ${tooltip(hint)}></i>` : "")
    );
  }
  if (column.renderer === "groups_renderer") {
    const groups = (value ?? []) as SummaryGroup[];
    return display
      ? groups
          .map(
            (group) =>
              `<span class="badge text-bg-info me-1" ${tooltip(group.id)}>${escapeHtml(group.display_name)}</span>`,
          )
          .join("")
      : groups.map((group) => group.display_name).join(", ");
  }
  if (column.renderer === "tags_renderer") {
    const tags = (value ?? []) as SummaryTag[];
    return display
      ? tags
          .map(
            (tag) =>
              `<span class="badge text-bg-${escapeHtml(tag.severity)} p-1 me-1" ${tooltip(tag.description ?? "-")}>${escapeHtml(tag.label)}</span>`,
          )
          .join("")
      : tags.map((tag) => tag.label).join(" ");
  }
  if (column.renderer === "comments_renderer") {
    const comments = (value ?? []) as SummaryComment[];
    const shown = comments.filter((comment) => comment.displayed);
    if (!display) return shown.map((comment) => `${comment.comment} ${comment.username}`).join(" ");
    if (!comments.length) return "";
    const hint = shown
      .map(
        (comment) =>
          `<p class='mb-1'>${escapeHtml(comment.comment)}</p><p class='mt-0 text-end fst-italic'>- ${escapeHtml(comment.username)}</p><hr>`,
      )
      .join("");
    return `<span class="badge text-bg-primary" ${tooltip(hint, true)}><i class="bi bi-chat-right"></i> ${comments.length}</span>`;
  }
  if (column.renderer === "date_renderer") {
    // Date criteria compare the displayed day, while sorting retains the full
    // timestamp so uploads on the same day remain in chronological order.
    if (type === "sort" || type === "type") return text(value);
    const date = value ? String(value).slice(0, 10) : "";
    return display ? escapeHtml(date || "-") : date;
  }
  if (column.renderer === "number_renderer") {
    if (!display) return typeof value === "number" ? value : text(value);
    return typeof value === "number"
      ? value.toLocaleString("en-US", { maximumFractionDigits: 20 })
      : escapeHtml(text(value));
  }
  if (column.renderer === "boolean_renderer" && display) {
    return `<i class="bi bi-${value ? "check-lg" : "x"}"></i>`;
  }
  return display ? escapeHtml(text(value)) : text(value);
}

export async function loadOverviewTable(table: HTMLTableElement): Promise<Config> {
  const response = await fetch(table.dataset.source, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`Sample overview request failed (${response.status})`);
  const data: OverviewData = await response.json();
  // Headers and data may come from separate API requests during an upgrade.
  // Match by ID, and fail explicitly rather than displaying shifted columns.
  const byId = new Map(data.columns.map((column) => [column.id, column]));
  const headers = Array.from(table.querySelectorAll<HTMLTableCellElement>("thead th"));
  const columns = headers.map((header) => {
    const column = byId.get(header.dataset.columnId);
    if (!column) throw new Error(`Missing summary column: ${header.dataset.columnId}`);
    header.dataset.filterable = String(column.filterable);
    return {
      data: column.id,
      defaultContent: "",
      orderable: column.sortable,
      searchable: column.searchable,
      visible: column.visible,
      type:
        column.type === "date"
          ? "date"
          : ["number", "integer"].includes(column.type)
            ? "num"
            : "string",
      render: (value: unknown, type: string) =>
        renderSummaryCell(column, value, type, table.dataset.sampleUrl),
    };
  });
  return {
    data: data.rows,
    columns,
    rowId: "sample_id",
    deferRender: true,
    createdRow: (row, _data, index) => {
      row.dataset.testId = `sample-row-${index + 1}`;
    },
  };
}
