import Choices, { InputChoice } from "choices.js";

const template = document.createElement("template");
template.innerHTML = String.raw`
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/base.min.css"/>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css"/>
<select id="select"></select>
`;

export type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

export class ChoiceSelect extends HTMLElement {
  private shadow!: ShadowRoot;
  private selectElement!: HTMLSelectElement;
  private choiceElement!: Choices;

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadow = this.shadowRoot!;
    this.shadow.appendChild(template.content.cloneNode(true));
    this.selectElement = this.shadow.getElementById("select") as HTMLSelectElement;
  }

  connectedCallback(): void {
    const isMultipleMode = this.hasAttribute("multiple");
    if (isMultipleMode) {
      this.selectElement.setAttribute("multiple", "");
    } else {
      this.selectElement.removeAttribute("multiple");
    }

    if (!this.choiceElement) {
      this.choiceElement = new Choices(this.selectElement, {
        placeholderValue: "Add to group",
        removeItemButton: isMultipleMode,
        itemSelectText: "",
        shouldSort: false,
        renderChoiceLimit: 20,
        searchResultLimit: 50,
        shadowRoot: this.shadow,
      });
    }

    this.selectElement.addEventListener("change", this.emitChange);
  }

  disconnectedCallback(): void {
    this.selectElement.removeEventListener("change", this.emitChange);
  }

  /*
   * Replace all choices (options) in the dropdown.
   * Optionally set preselected values (single or multi).
   */
  setChoices(options: SelectOption[], preselected?: string | string[]) {
    // Clear existing choices and selection safely
    this.choiceElement.clearStore(); // clear all internal stores (choices & items)
    this.choiceElement.clearChoices(); // clear <option> list

    // Map to InputChoice format
    const data: InputChoice[] = options.map((o) => ({
      value: o.value,
      label: o.label,
      disabled: !!o.disabled,
      selected: false, // we’ll handle selection below
    }));

    this.choiceElement.setChoices(data, "value", "label", false);
  }

  /*
   * Programmatically set the selection (single or multiple).
   * Values must match existing choice values.
   */
  setSelected(values: string | string[]) {
    const val = Array.isArray(values) ? values : [values];
    // Clear previous items in a controlled way
    this.choiceElement.removeActiveItems();
    this.choiceElement.setChoiceByValue(val);
  }

  /*
   * Get selected values as primitives (string[]) in multi mode or [string] in single.
   */
  getSelected(): string[] {
    const val = this.choiceElement.getValue(true);
    // getValue(true) returns string for single and array for multiple; normalize to array
    return Array.isArray(val) ? val : val ? [val] : [];
  }

  /* Clear selection but keeps choicese */
  clearSelected(): void {
    this.choiceElement.removeActiveItems();
  }

  private emitChange = () => {
    const values = this.getSelected();
    this.dispatchEvent(
      new CustomEvent("change", {
        detail: { values },
        bubbles: true,
        composed: true,
      }),
    );
  };
}

customElements.define("choice-select", ChoiceSelect);
