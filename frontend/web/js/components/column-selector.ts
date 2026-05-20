console.log("[ColumnSelector] module evaluated");

import Sortable from "sortablejs";

interface ColumnItem {
  id: string;
  label: string;
  enabled: boolean;
}

class ColumnSelector extends HTMLElement {
  private _items: ColumnItem[] = [];
  private sortable?: Sortable;

  set items(items: ColumnItem[]) {
    this._items = items;
    this.render();
  }

  get items(): ColumnItem[] {
    return this._items;
  }

  connectedCallback() {
    this.render();
  }

  private render() {
    this.innerHTML = String.raw`
      <ul class="list-group ge-columns-list">
        ${this._items
          .map(
            item => `
          <li
            class="list-group-item d-flex align-items-center ge-column-item
                   ${item.enabled ? "" : "is-disabled"}"
            data-id="${item.id}"
          >
            <div class="form-check me-3">
              <input
                class="form-check-input ge-column-checkbox"
                type="checkbox"
                ${item.enabled ? "checked" : ""}
              />
            </div>

            <span class="flex-grow-1 ge-column-label">
              ${item.label}
            </span>

            <span class="drag-handle text-muted ms-2">
              <i class="bi bi-list"></i>
            </span>
          </li>
        `
          )
          .join("")}
      </ul>
    `;

    this.wireCheckboxes();
    this.initSortable();
  }

  private wireCheckboxes() {
    this.querySelectorAll(".ge-column-item").forEach(itemEl => {
      const checkbox = itemEl.querySelector<HTMLInputElement>(
        ".ge-column-checkbox"
      )!;
      const id = itemEl.getAttribute("data-id")!;

      checkbox.addEventListener("change", () => {
        this._items = this._items.map(item =>
          item.id === id
            ? { ...item, enabled: checkbox.checked }
            : item
        );

        this.dispatchChange();
        this.render();
      });
    });
  }

  private initSortable() {
    const colList = this.querySelector(".ge-columns-list");
    if (!colList) return;

    if (this.sortable) {
        this.sortable?.destroy();
        this.sortable = undefined;
    }
    Sortable.create(colList, {
        handle: ".drag-handle",
        animation: 150,
        filter: ".is-disabled",
        preventOnFilter: false,
        onEnd: () => this.updateOrderFromDOM()
    });
  }

  private updateOrderFromDOM() {
    const ids = Array.from(
      this.querySelectorAll<HTMLElement>(".ge-column-item:not(.is-disabled)")
    ).map(el => el.dataset.id!);

    const enabled = this._items.filter(i => i.enabled);
    const disabled = this._items.filter(i => !i.enabled);

    const reordered = ids.map(id => enabled.find(i => i.id === id)!);

    this._items = [...reordered, ...disabled];
    this.dispatchChange();
  }

  private dispatchChange() {
    this.dispatchEvent(
      new CustomEvent("column-selector:change", {
        detail: { items: this._items },
        bubbles: true,
      })
    );
  }
}

customElements.define("column-selector", ColumnSelector);