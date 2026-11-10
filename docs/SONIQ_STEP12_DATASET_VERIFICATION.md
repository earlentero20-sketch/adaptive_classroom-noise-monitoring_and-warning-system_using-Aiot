# SONIQ Step 12 Dataset Verification

- Archive: $archive; checksum manifest: $manifest.
- 69 source files represented (58 audio recordings plus 11 CSV/JSON metadata and manifest files); source size 897,952,250 bytes.
- Archive size: 726773613 bytes; SHA-256: $zipHash.
- ZIP opens; all 69 expected entries are present and match their per-file SHA-256 values. Result: PASS.
- Dataset folder hierarchy and original names remain in the archive. No original files were moved or altered during Step 12.
- Archive is still in the system Temp directory, not confirmed in durable storage. Recommended durable destination: a dedicated SONIQ_TRANSFER folder on an external drive or approved backup location, separate from the Git repository. No move was performed.
