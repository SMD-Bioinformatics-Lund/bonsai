import * as bootstrap from "bootstrap";
import jQuery from "jquery";

import { throwSmallToast } from "./notification";

export const initToast = () => { 
    // init toasts
    const toastElList = [].slice.call(document.querySelectorAll(".toast"));
    const toastList = toastElList.map((toastEl) => {
        return new bootstrap.Toast(toastEl);
    });
};

declare global {
    interface Window {
        throwSmallToast: (message: string) => void;
        jQuery: typeof jQuery;
        $: typeof jQuery;
    }
}

window.throwSmallToast = throwSmallToast;
window.jQuery = jQuery;
window.$ = jQuery;