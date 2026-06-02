import { initToast, initTooltip } from "../../utils/notification";
import { initSetSampleQc, updateQcStatus, findAndClusterSimilarSamples } from "../../core/actions/sample-actions";
import { createSampleViewApi } from "./api";

export async function initSampleView(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
  sampleId: string,
  groupId: string | null,
): Promise<string> {
  const api = createSampleViewApi(bonsaiApiUrl, accessToken, refreshToken);
  initToast();
  initTooltip();

  const qcStatusForm = document.getElementById("qc-classification-form") as HTMLButtonElement;
  if (qcStatusForm) {
    initSetSampleQc(() => [sampleId], api.setSampleQc.bind(api), updateQcStatus, qcStatusForm);
  }

  let narrow_search_to = null;
  if (groupId !== null) {
    const group = await api.getGroup(groupId);
    narrow_search_to = group.included_samples.length > 0 ? group.included_samples : null;
  }

  return await findAndClusterSimilarSamples(sampleId, narrow_search_to, api);
}

// Backwards-compatible global for templates
(window as any).initSampleView = initSampleView;
