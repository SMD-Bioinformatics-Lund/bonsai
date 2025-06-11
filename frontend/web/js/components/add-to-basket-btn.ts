import { LitElement, html } from "lit";
import { customElement } from "lit/decorators.js";

@customElement("add-to-basket-btn")
export class AddToBasketButton extends LitElement {
  protected createRenderRoot(): HTMLElement | DocumentFragment {
    return this; // use light DOM to allow bootstrap styling and external access
  }

  render() {
    return html`
      <button
        id="add-to-basket-btn"
        class="btn btn-sm btn-outline-success"
        data-test-id="add-to-basket-btn"
        disabled
      >
        <i class="bi bi-plus-lg"></i>
        <span>Add to basket</span>
      </button>
    `;
  }
}
