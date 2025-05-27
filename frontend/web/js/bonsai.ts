import * as bootstrap from "bootstrap";
import jQuery from "jquery";

import { throwSmallToast } from "./notification";
import { ApiService, AuthService, HttpClient } from "./api";
import { initializeSamplesTable } from "./table";
import { clusterSamples, SampleBasket, SamplesInBasketCounter } from "./basket";
import { addSelectedSamplesToGroup, deleteSelectedSamples, getSimilarSamplesAndCheckRows } from "./sample";

export function initialize(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): {
  api: ApiService;
  basket: SampleBasket;
  clusterSamplesInBasket: (element: HTMLElement) => void;
} {
  // initialize API
  const auth = new AuthService(bonsaiApiUrl);
  auth.setTokens(accessToken, refreshToken);
  const http = new HttpClient(bonsaiApiUrl, auth);
  const api = new ApiService(http);

  // init sample basket and basket counter
  const basket = new SampleBasket(api.getSamplesDetails);
  const basketCounter = new SamplesInBasketCounter();
  basketCounter.counter = basket.getSampleIds.length;
  // register callback functions
  basket.onSelection((sampleIds: string[]) => {
    basketCounter.counter = sampleIds.length;
  });

  const clusterSamplesInBasket = (element) =>
    clusterSamples(element, basket.getSampleIds(), api);

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

  return {
    api: api,
    basket: basket,
    clusterSamplesInBasket: clusterSamplesInBasket,
  };
}

declare global {
  interface Window {
    throwSmallToast: (message: string) => void;
    initSampleTbl: typeof initializeSamplesTable;
    getSimilarSamplesAndCheckRows: typeof getSimilarSamplesAndCheckRows;
    addSelectedSamplesToGroup: typeof addSelectedSamplesToGroup;
    deleteSelectedSamples: typeof deleteSelectedSamples;
    jQuery: typeof jQuery;
    $: typeof jQuery;
    bootstrap: typeof bootstrap;
  }
}

window.throwSmallToast = throwSmallToast;
window.jQuery = jQuery;
window.$ = jQuery;
window.initSampleTbl = initializeSamplesTable;
window.bootstrap = bootstrap;
window.addSelectedSamplesToGroup = addSelectedSamplesToGroup;
window.deleteSelectedSamples = deleteSelectedSamples;
window.getSimilarSamplesAndCheckRows = getSimilarSamplesAndCheckRows;
