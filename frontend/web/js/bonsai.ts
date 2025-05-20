import * as bootstrap from "bootstrap";
import jQuery from "jquery";

import { throwSmallToast } from "./notification";
import { ApiService, AuthService, HttpClient } from "./api";
import { getSimilarSamplesV2, initializeSamplesTable } from "./table";

export function initialize(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): ApiService {
  // initialize API
  const auth = new AuthService(bonsaiApiUrl);
  auth.setTokens(accessToken, refreshToken);
  const client = new HttpClient(bonsaiApiUrl, auth);
  const api = new ApiService(client);

  // init toasts and tooltips
  const toastElList = [].slice.call(document.querySelectorAll(".toast"));
  const toastList = toastElList.map((toastEl) => {
    return new bootstrap.Toast(toastEl);
  });
  const tooltipTriggerList = document.querySelectorAll(
    '[data-bs-toggle="tooltip"]',
  );
  const tooltipList = [...tooltipTriggerList].map(
    (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl),
  );

  return api;
}

declare global {
  interface Window {
    throwSmallToast: (message: string) => void;
    getSimilarSamplesV2: typeof getSimilarSamplesV2;
    initSampleTbl: typeof initializeSamplesTable;
    jQuery: typeof jQuery;
    $: typeof jQuery;
  }
}

window.getSimilarSamplesV2 = getSimilarSamplesV2;
window.throwSmallToast = throwSmallToast;
window.jQuery = jQuery;
window.$ = jQuery;
window.initSampleTbl = initializeSamplesTable;
