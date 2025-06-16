// functions for hide/ showing spinner
export const showSpinner = (containerElement: HTMLElement): void => {
  // show spinner and hide content
  const content = containerElement.querySelector(
    ".content",
  ) as HTMLButtonElement;
  const spinner = containerElement.querySelector(".loading") as HTMLSpanElement;
  content.classList.add("d-none");
  content.disabled = true;
  spinner.classList.remove("d-none");
};

export const hideSpinner = (containerElement: HTMLElement): void => {
  // hide spinner and show content
  const content = containerElement.querySelector(
    ".content",
  ) as HTMLButtonElement;
  const spinner = containerElement.querySelector(".loading") as HTMLSpanElement;
  content.classList.remove("d-none");
  content.disabled = false;
  spinner.classList.add("d-none");
};
