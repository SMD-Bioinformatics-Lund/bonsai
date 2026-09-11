// Compatibility setup for the current UUID-based API and the PRP bootstrapper.
// PRP's bootstrap config contains stable group IDs, but the API currently
// generates UUIDs and PRP does not add uploaded samples to those groups.

const groupSpecs = [
    {
        stableId: "mtuberculosis",
        displayName: "M. tuberculosis",
        samplePattern: /^synthetic_tb_/,
    },
    {
        stableId: "saureus",
        displayName: "S. aureus",
        samplePattern: /^synthetic_sa_/,
    },
];

groupSpecs.forEach(function (spec) {
    const group = db.sample_group.findOne({"core.display_name": spec.displayName});
    if (group === null) {
        throw new Error("Missing bootstrapped test group: " + spec.displayName);
    }

    db.sample_group.updateOne(
        {_id: group._id},
        {$set: {"core.group_id": spec.stableId, modified_at: new Date()}},
    );

    const sampleQuery = {external_sample_id: spec.samplePattern};
    const sampleCount = db.sample.count(sampleQuery);
    if (sampleCount !== 5) {
        throw new Error(
            "Expected 5 samples for " + spec.stableId + ", found " + sampleCount,
        );
    }

    db.sample.updateMany(
        sampleQuery,
        {$set: {groups: [spec.stableId], modified_at: new Date()}},
    );
    db.sample_group.updateOne(
        {_id: group._id},
        {$set: {"core.sample_count": sampleCount, modified_at: new Date()}},
    );
});

print("Assigned synthetic samples to stable local-test groups.");
