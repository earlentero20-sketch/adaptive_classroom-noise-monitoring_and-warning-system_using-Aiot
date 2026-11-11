# SONIQ Step 12 Manifest Comparison

Source manifest: SONIQ_COMPLETE_HANDOFF_MANIFEST.md from handoff ref $ref.

- Manifest table has 127 rows because the seven model artifact paths appear twice (dedicated artifact inventory and complete inventory); 120 unique listed payload paths.
- Handoff tree contains 121 files, including the manifest itself. All 120 unique payload paths are present in that tree; there are no duplicate unique paths.
- SHA-256 and byte verification against Git blob bytes or the Git Windows-filtered checkout representation: 117/120 unique paths match. Three unresolved differences: SONIQ_COMPLETE_HANDOFF_PUBLISH_PLAN.md, SONIQ_HANDOFF_EXCLUSIONS.md, and SONIQ_SECOND_PC_SETUP_GUIDE.md.
- Compared with the current PC-49 working files: 40 manifest-listed paths are absent; 9 existing paths differ in byte size and SHA-256; 71 paths match. Missing files are primarily handoff reports/setup additions and handoff-only code/protocol files. No files were copied to resolve this.
- The current workspace has many additional files outside this 121-file snapshot, chiefly its local ML virtual environment, classroom data, and Step 11 reports. These are not inferred to be unwanted.
- No conflicts were resolved. Do not assemble a package claiming a fully verified manifest until the three manifest-to-tree differences are resolved or explicitly accepted and the 40 absent files are provided in the selected package source.
