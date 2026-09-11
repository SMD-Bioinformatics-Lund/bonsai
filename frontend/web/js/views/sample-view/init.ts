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

  let narrow_search_to: string[] | null = null;
  if (groupId !== null) {
    const group = await api.getGroup(groupId);
    if (group.sample_count > 0) {
      const memberships = await api.getMembershipByGroups([groupId]);
      const sampleIds = Array.from(new Set(memberships.map((edge) => edge.sample_id)));
      narrow_search_to = sampleIds.length > 0 ? sampleIds : null;
    }
  }

  return await findAndClusterSimilarSamples(sampleId, narrow_search_to, api);
}

// Backwards-compatible global for templates
Object.assign(window, { initSampleView });
