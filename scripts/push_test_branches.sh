#!/usr/bin/env bash
# Push the 44 final-report fix candidates and five related test/report branches.
# This script is for the user to run. It creates no PRs and never force-pushes.
# --dry-run checks local refs and prints commands without contacting any remote.
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash push_test_branches.sh [--dry-run]

Default: check every local ref, check all four destinations with git push
--dry-run, then push each repository's selected branches atomically.

--dry-run only checks local refs and prints the planned push commands.
No remote is contacted in this preview mode.

Repositories/remotes can be overridden with these environment variables:
  BONSAI_REPO  BONSAI_REMOTE  (default: /home/jakob/src/codex/bonsai, origin)
  SDK_REPO     SDK_REMOTE     (default: nested bonsai-sdk checkout, origin)
  PRP_REPO     PRP_REMOTE     (default: /home/jakob/src/codex/bonsai-prp, origin)
  JASEN_REPO   JASEN_REMOTE   (default: prepared JASEN checkout, origin)

Each *_REMOTE accepts a configured remote name or a repository URL.
For example, JASEN_REMOTE=git@github.com:YOUR_ACCOUNT/jasen.git can target
an existing fork instead of genomic-medicine-sweden/jasen.

The fixed candidate refs must still match the final report's commits.
The report branch may have advanced from the final-report commit.
Only the 49 named branches are pushed; development/master and tags are excluded.
Atomicity applies within each repository, not across the four repositories.
If a push fails, resolve the reported cause and rerun; completed pushes are safe
to repeat. Remote divergence is rejected rather than overwritten.
Generated PDFs, test data and running instances are not transferred by Git.
USAGE
}

publish_preview=false
case "${1:-}" in
  '') ;;
  --dry-run) publish_preview=true ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
if (( $# > 1 )); then usage >&2; exit 2; fi

declare -a publish_order=(sdk prp jasen bonsai)
declare -A publish_repos=(
  [bonsai]="${BONSAI_REPO:-/home/jakob/src/codex/bonsai}"
  [sdk]="${SDK_REPO:-${BONSAI_REPO:-/home/jakob/src/codex/bonsai}/bonsai-sdk}"
  [prp]="${PRP_REPO:-/home/jakob/src/codex/bonsai-prp}"
  [jasen]="${JASEN_REPO:-/home/jakob/data/codex/jasen/environments/jasen-quoted-sample-name/source}"
)
declare -A publish_remotes=(
  [bonsai]="${BONSAI_REMOTE:-origin}"
  [sdk]="${SDK_REMOTE:-origin}"
  [prp]="${PRP_REMOTE:-origin}"
  [jasen]="${JASEN_REMOTE:-origin}"
)
declare -A publish_refspecs=()
declare -A publish_counts=()

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

for publish_key in "${publish_order[@]}"; do
  git -C "${publish_repos[$publish_key]}" rev-parse --git-dir >/dev/null ||
    die "Repository unavailable: ${publish_repos[$publish_key]}"
  publish_dest=${publish_remotes[$publish_key]}
  [[ "$publish_dest" != -* ]] || die "Invalid destination: $publish_dest"
  case "$publish_dest" in
    *://*|*@*:*) publish_url=$publish_dest ;;
    *)
      publish_url=$(git -C "${publish_repos[$publish_key]}" remote get-url --push --all "$publish_dest") ||
        die "Cannot resolve $publish_key remote: $publish_dest"
      [[ "$publish_url" != *$'\n'* ]] ||
        die "Multiple push URLs for $publish_key; select a single destination with its *_REMOTE override"
      ;;
  esac
  printf '%s -> %s\n' "$publish_key" "$publish_url"
done

# Repository key | branch | exact reported head (ancestor: allows report updates).
while IFS='|' read -r publish_key publish_branch publish_expected; do
  [[ -n "$publish_key" && "$publish_key" != \#* ]] || continue
  publish_actual=$(git -C "${publish_repos[$publish_key]}" rev-parse --verify "refs/heads/$publish_branch") ||
    die "Missing $publish_key branch: $publish_branch"
  case "$publish_expected" in
    ancestor:*)
      git -C "${publish_repos[$publish_key]}" merge-base --is-ancestor \
        "${publish_expected#ancestor:}" "$publish_actual" ||
        die "Report branch no longer descends from the final-report commit: $publish_branch"
      ;;
    *) [[ "$publish_actual" == "$publish_expected" ]] ||
      die "$publish_key $publish_branch moved from its recorded commit; review and update the script before publishing" ;;
  esac
  # Use the verified commit as the source, so a moving local ref cannot change
  # what is sent between the preflight and push. No checkout is necessary.
  publish_refspecs[$publish_key]+="$publish_actual:refs/heads/$publish_branch"$'\n'
  publish_counts[$publish_key]=$(( ${publish_counts[$publish_key]:-0} + 1 ))
done <<'BRANCHES'
bonsai|pr/ordinary-record-delete|e07c608476803971b48e980fe1ffb318a2f2db0a
bonsai|pr/account-role-permissions|5b7e90594dde4b4b514eef8d45db46162da499ea
bonsai|pr/analysis-upload-role-gate|dd5c2481be225712b0b4ae0565d7b701b4c4686e
bonsai|pr/private-record-scope|ce4fa9e1779d0b3f08e3630520565ca3d01cd57e
bonsai|pr/group-delete-membership-loss|5861b369bc71470a980ae4aed3911937df109fb7
bonsai|pr/group-membership-loss|0e782307e2551a6c3afad00b5595bb6417e9624f
bonsai|pr/metadata-add-500|e767620b6d62b0dcbb9530147461280e22a7fbef
bonsai|pr/recovery-metadata-loss|d7ee2464e82811107129ca462acd6cb6189d4603
bonsai|pr/recovery-comment-identities|34cbe08fed81255fd3d8d3d45b9763aabe5af934
bonsai|pr/recovery-group-overlap|e049aec434621b10c094ff6888dda27abf8dec3f
bonsai|pr/metadata-category-loss|13a4b49e3f6b50e8c717af6db068eb29d6a6273b
bonsai|pr/metadata-table-empty|fa643f1d987e4b90a25f3bcd530581c19651e44e
bonsai|pr/csv-empty-cell-500|9811fa547b554c5b5dee2e6e742bca8d2b0deb2f
bonsai|pr/curation-double-submit|aa554c2ad2cbb0adf9eccf8487b237bdc9a583e0
bonsai|pr/recovery-comment-retry|66a99c96e7fa3478d7ab7bee23a98e3723e08502
bonsai|pr/selected-filter-stale|859f603e8db62593a71518b29a35e1bf11917a2c
bonsai|pr/variant-select-all-invalid|6d08d7abd5256440ad9f0c74b25e77b7c0ac5b5a
bonsai|pr/variant-filter-and|16fb3d32d5b9694365c3880eb2cb63b05eb08e5e
bonsai|pr/variant-hide-dismissed-500|20bbb27b2f85c82a25557aa2527f65f009c02019
bonsai|pr/qc-filter-empty|77b75326f97936382633c001a9ee7a562b48a824
bonsai|pr/group-membership-limit|6ddfd15b2c4f9c439ec561999b56fa4aea73d1a8
bonsai|pr/admin-create-user-500|e01528db104ccb7d392441f42cfe742ee45f5e8e
bonsai|pr/admin-edit-user-500|619cab28e4bf8f8706a391804b017442090106aa
bonsai|pr/account-stale-pages|8567eda7b11457fa7619fc9fe30f7e21d0ba14ad
bonsai|pr/basket-undefined-assay|a011b68355535d49b70ddbebaf38d8e572869fe0
bonsai|pr/private-group-invite-500|1b1d4b7e97c6b02bd54d5990c93bca743b879e3b
bonsai|pr/pending-sample-500|f24e6a59cbd5aa2e9b98cd427f278ac05277910b
bonsai|pr/tb-curation-500|d2218de5ec04515bdc642ab509f902dbc397be5f
bonsai|pr/tb-no-amr-500|e6d57246675b3a8b91de544d67792b4e9e0197c2
bonsai|pr/ecoli-variants-empty|4bd99d441ff66b7e1d013d5af6bbd3d0394b1edc
bonsai|pr/emm-display-missing|a883d776f67a72980235c7fbc857ab39c8a64eff
bonsai|pr/display-emm-table|ca7a7c22cc5f95a3868e4e314d2313a9b9068c94
bonsai|pr/display-extended-context|45d812d891084c38064a2348f5d495c3d4d0efe3
bonsai|pr/emm-lims-export-500|3aeb54797bab82ed33fc78ef7ee190bfbe3a78e1
bonsai|pr/kleborate-upload-422|6547f49a7312aa1ba12eeeeccaa2be7e068b5ce7
bonsai|pr/index-write-authentication|f2d8992b9e66abfdda5ff3fcfb0a58874edfba50
sdk|pr/parser-mykrobe-selection|3183b86d7aec72309b62e656ac3c969abba2fe7f
sdk|pr/parser-bracken-empty|019d5904bd59eb58a6399ac02ba49c4106b93490
sdk|pr/parser-coverage-stream|1cd7ad6ec984aafea2386fe9156123ae7f2cb04d
sdk|pr/kleborate-client-companion|e9c6d609da6a2c4c7c447026a71df8973c1cf78b
sdk|pr/parser-read-pair-count|f0fdc9e9fc82bb90733363408770d6c0daebfdba
sdk|pr/kleborate-kaptive-nesting|c04cc720a3e3789efeb507e083cf2ce781997074
prp|pr/kleborate-companion-upload|80d3a012273bda5554783db07d4d89d5d1ccffd4
jasen|pr/quote-producer-sample-name|48736c6dcf9c239dc7618115abb6c7fcf84821c4
# Related test, combined-fix and report source branches.
bonsai|test/species-ui-release-pass|07be8af48df507fca50e39cd295cc41d4a442c0f
bonsai|fix/critical-ui-release-pass|c5c62e37a4d7729a1774b1d14c766a6cb3a964fd
bonsai|test/jasen-public-reference-pilot|fb68e306ccf9858a9aecff737e96fccea647091a
bonsai|test/bonsai-organism-coverage|ancestor:a71cdc570e766ee187593941a0a20f0d8802f6e0
sdk|fix/parser-display-fidelity|ecf07a8ef079cee5916b50427e508480e2a2e1ff
BRANCHES

publish_total=0
for publish_key in "${publish_order[@]}"; do
  publish_total=$(( publish_total + ${publish_counts[$publish_key]} ))
  printf 'Verified %s: %s branches\n' "$publish_key" "${publish_counts[$publish_key]}"
done
[[ "$publish_total" == 49 ]] || die "Unexpected branch total: $publish_total (expected 49)"

push_repository() {
  local publish_key=$1 publish_mode=$2
  local -a publish_args publish_refs
  mapfile -t publish_refs < <(printf '%s' "${publish_refspecs[$publish_key]}")
  publish_args=(git -C "${publish_repos[$publish_key]}" push --atomic --no-follow-tags --recurse-submodules=no)
  if [[ "$publish_mode" == preflight ]]; then publish_args+=(--dry-run); fi
  publish_args+=(-- "${publish_remotes[$publish_key]}" "${publish_refs[@]}")
  if "$publish_preview"; then
    printf '  '; printf '%q ' "${publish_args[@]}"; printf '\n'
  else
    "${publish_args[@]}"
  fi
}

if "$publish_preview"; then
  printf '\nPreview only: 49 branches checked locally; no remote contacted.\n'
  for publish_key in "${publish_order[@]}"; do push_repository "$publish_key" push; done
  exit 0
fi

# A permission/divergence failure here prevents every real push.
printf '\nChecking all four push destinations before publishing...\n'
for publish_key in "${publish_order[@]}"; do push_repository "$publish_key" preflight; done

for publish_key in "${publish_order[@]}"; do
  printf '\nPushing %s (%s branches)...\n' "$publish_key" "${publish_counts[$publish_key]}"
  push_repository "$publish_key" push
done
printf '\nCompleted: 49 branches pushed across four repositories.\n'
