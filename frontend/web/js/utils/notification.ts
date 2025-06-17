import * as bootstrap from "bootstrap";

export const throwSmallToast = (message: string, type: string = "info") => {
  // get template toast element
  const toastTemplate = document.getElementById(
    "small-toast-template",
  ) as HTMLTemplateElement | null;
  if (toastTemplate !== undefined) {
    // copy new element
    const toastElement = toastTemplate.content
      .querySelector(".toast")
      .cloneNode(true) as HTMLDivElement;

    // append new toast to DOM
    const toastContainer = document.getElementById("toast-container");
    toastContainer.appendChild(toastElement);

    // instanciate new toast element
    const toast = new bootstrap.Toast(toastElement);

    // select button
    const btn = toastElement.querySelector("button");
    //const toast = bootstrap.Toast.getInstance(toastElement)
    // style toast depending on type
    switch (type) {
      case "info":
        toast._element.classList.add("text-bg-secondary");
        btn.classList.add("btn-close-white");
        break;
      case "success":
        toast._element.classList.add("text-bg-success");
        btn.classList.add("btn-close-white");
        break;
      case "warning":
        toast._element.classList.add("text-bg-warning");
        break;
      case "error":
        toast._element.classList.add("text-bg-danger");
        btn.classList.add("btn-close-white");
        break;
    }
    const errorMessage = toast._element.querySelector("#toast-error-message");
    // add custom error message
    errorMessage.innerText = message;
    toast.show();
  }
};

/* Setup bootstrap toast */
export function initToast() {
  const toastElList = [].slice.call(document.querySelectorAll(".toast"));
  toastElList.map((toastEl) => {
    return new bootstrap.Toast(toastEl);
  });
}

export function initTooltip() {
  const tooltipTriggerList = document.querySelectorAll(
    '[data-bs-toggle="tooltip"]',
  );
  [...tooltipTriggerList].map(
    (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl),
  );
}
