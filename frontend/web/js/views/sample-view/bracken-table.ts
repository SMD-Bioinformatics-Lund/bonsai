export function initBrackenTables(): void {
  document.querySelectorAll<HTMLElement>("[data-bracken-results]").forEach((container, index) => {
    const button = container.querySelector<HTMLButtonElement>("[data-bracken-toggle]");
    const body = container.querySelector<HTMLTableSectionElement>("tbody");
    if (!button || !body) return;

    const extraRows = Array.from(body.rows).slice(5);
    if (extraRows.length === 0) return;
    body.id = `bracken-species-${index}`;
    button.setAttribute("aria-controls", body.id);

    const setExpanded = (expanded: boolean) => {
      extraRows.forEach(row => { row.hidden = !expanded; });
      button.setAttribute("aria-expanded", String(expanded));
      button.textContent = expanded ? "Show less" : `Show more (${extraRows.length})`;
    };
    setExpanded(false);
    button.hidden = false;
    button.addEventListener("click", () => {
      setExpanded(button.getAttribute("aria-expanded") !== "true");
    });
  });
}
