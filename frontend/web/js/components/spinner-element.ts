import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('spinner-element')
export class SpinnerElement extends LitElement {
  static styles = css`
    .d-flex {
      display: flex;
      justify-content: center;
    }
    .loading {
      margin-top: 3rem;
      margin-bottom: 3rem;
    }
    .spinner-border {
      color: var(--bs-success, #198754);
      width: 2rem;
      height: 2rem;
      border-width: 0.25em;
      display: inline-block;
      vertical-align: text-bottom;
      border: 0.25em solid currentColor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spinner-border .75s linear infinite;
    }
    @keyframes spinner-border {
      to { transform: rotate(360deg); }
    }
    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0,0,0,0);
      border: 0;
    }
  `;

  static properties = {
    visible: { type: Boolean, reflect: true }
  };

  visible: boolean = true;

  show() {
    this.visible = true;
  }

  hide() {
    this.visible = false;
  }

  render() {
    return this.visible ? html`
      <div class="d-flex justify-content-center loading my-5">
        <div class="spinner-border text-success" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    ` : html``;
  }
}

export default SpinnerElement;