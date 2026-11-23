import { initToast, initTooltip } from "../../utils/notification";
import { initSetSampleQc, updateQcStatus, findAndClusterSimilarSamples } from "../../core/actions/sample-actions";
import type { SampleViewApi } from "./api";
import { initBrackenTables } from "./bracken-table";

export function initSampleSidebar(sampleId: string, api: SampleViewApi): void {
  initToast();
  initTooltip();

  const qcStatusForm = document.getElementById("qc-classification-form");
  if (qcStatusForm) {
    initSetSampleQc(() => [sampleId], api.setSampleQc.bind(api), updateQcStatus, qcStatusForm);
  }
}

export async function initSampleSummary(
  sampleId: string,
  groupId: string | null,
  api: SampleViewApi,
): Promise<string | null> {
  initBrackenTables();

  let narrow_search_to: string[] | null = null;
  if (groupId !== null) {
    const group = await api.getGroup(groupId);
    const scope = document.getElementById("similar-samples-scope");
    if (scope) {
      scope.textContent = `in group: ${group.display_name}`;
    }
    if (group.sample_count > 0) {
      const memberships = await api.getMembershipByGroups([groupId]);
      const sampleIds = Array.from(new Set(memberships.map((edge) => edge.sample_id)));
      narrow_search_to = sampleIds.length > 0 ? sampleIds : null;
    }
  }

  return await findAndClusterSimilarSamples(sampleId, narrow_search_to, api);
}
