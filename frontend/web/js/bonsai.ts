import * as bootstrap from "bootstrap";
import jQuery from "jquery";

import { throwSmallToast } from "./notification";
import { ApiService, AuthService, HttpClient } from "./api";
import { getSimilarSamplesV2, initializeSamplesTable } from "./table";
import { SampleBasket, SamplesInBasketCounter } from "./basket";

export function initialize(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): {api: ApiService, basket: SampleBasket} {
  // initialize API
  const auth = new AuthService(bonsaiApiUrl);
  auth.setTokens(accessToken, refreshToken);
  const http = new HttpClient(bonsaiApiUrl, auth);
  const api = new ApiService(http);

  // init sample basket and basket counter
  const basketState = new SampleBasket(api.getSamplesDetails)
  const basketCounter = new SamplesInBasketCounter()
  basketCounter.counter = basketState.getSampleIds.length
  // register callback functions
  basketState.onSelection((sampleIds: string[]) => {basketCounter.counter = sampleIds.length})

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

  return {api: api, basket: basketState};
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
