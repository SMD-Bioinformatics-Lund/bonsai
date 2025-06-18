import { BasketState } from "../state/basket-state";

export class SampleBasketCounter extends HTMLElement {
  private state: BasketState | null = null;
  private badgeElement: HTMLSpanElement | null = null;
  private counterElement: HTMLSpanElement | null = null;

  constructor() {
    super()
  }

  private updateCounter(value: number) {
    if (this.counterElement && this.badgeElement) {
      this.counterElement.textContent = value.toString()
      this.badgeElement.hidden = value === 0;
    }
  }

  private handleStateChange = (ids: string[]) => {
    this.updateCounter(ids.length)
  }

  set basketState(state: BasketState) {
    if (this.state) {
      this.state.offSelection(this.handleStateChange);
    }
    this.state = state;
    this.state.onSelection(this.handleStateChange);
    // initialize counter
    this.updateCounter(this.state.getSampleIds().length);
  }

  connectedCallback() {
    this.render();
  }

  disconnectedCallback() {
    if (this.state) {
      this.state.offSelection(this.handleStateChange);
    }
  }

  private render() {
    const nSamples = this.state?.getSampleIds().length
    this.innerHTML = String.raw`
      <span id="sample-basket-badge" ${nSamples === 0 ? 'hidden' : ''} class="position-absolute top-25 start-75 translate-middle badge rounded-pill bg-danger">
        <span id="sample-basket-counter" data-test-id="samples-in-basket-counter">${nSamples}</span>
        <span class="visually-hidden">Samples in basket</span>
      </span>
    `;
    this.badgeElement = this.querySelector("#sample-basket-badge");
    this.counterElement = this.querySelector("#sample-basket-counter");
  }
}

customElements.define("sample-basket-counter", SampleBasketCounter)