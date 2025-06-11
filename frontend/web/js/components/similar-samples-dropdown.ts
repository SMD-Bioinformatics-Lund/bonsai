import { LitElement, html } from "lit";
import { customElement } from "lit/decorators.js";

@customElement("similar-samples-dropdown")
export class SimilarSamplesDropdown extends LitElement {
  protected createRenderRoot(): HTMLElement | DocumentFragment {
    return this; // use light DOM for bootstrap styling
  }

  firstUpdated() {
    const searchBtn = this.querySelector(
      "#similar-samples-button",
    ) as HTMLButtonElement | null;
    if (searchBtn) {
      searchBtn.addEventListener("click", () => {
        const limit = parseInt(
          (this.querySelector("#similar-samples-limit") as HTMLInputElement).value,
        );
        const similarity = parseFloat(
          (this.querySelector("#similar-samples-threshold") as HTMLInputElement)
            .value,
        );
        this.dispatchEvent(
          new CustomEvent("search", {
            detail: { limit, similarity },
            bubbles: true,
          }),
        );
      });
    }
  }

  render() {
    return html`
      <div id="find-similar-dropdown" class="dropdown similar-samples-container">
        <button
          id="select-similar-samples-btn"
          class="btn btn-sm btn-outline-secondary dropdown-toggle ms-4"
          data-bs-toggle="dropdown"
          disabled
        >
          <span class="content">
            <i class="bi bi-search"></i>
            <span>Find similar</span>
          </span>
          <span class="loading align-middle d-none">
            <span class="spinner-grow text-success spinner-grow-sm" role="status"></span>
            Loading...
          </span>
        </button>
        <form class="dropdown-menu dropdown-menu-end p-2 needs-validation">
          <input
            type="text"
            name="similar-samples-limit"
            id="similar-samples-limit"
            class="form-control form-control-sm"
            placeholder="Number of samples"
            value="50"
            required
          />
          <input
            type="text"
            name="similar-samples-threshold"
            id="similar-samples-threshold"
            class="form-control form-control-sm mt-2"
            placeholder="Min similarity"
            value="0.95"
            required
          />
          <button
            type="button"
            id="similar-samples-button"
            class="btn btn-sm btn-outline-success mt-2"
          >
            <i class="bi bi-search"></i>
            Search
          </button>
        </form>
      </div>
    `;
  }
}
