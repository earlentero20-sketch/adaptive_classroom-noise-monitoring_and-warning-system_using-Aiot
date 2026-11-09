# SONIQ Handoff Exclusions

This snapshot intentionally excludes the following from the second-PC handoff:

- `.env`, credentials, passwords, tokens, private machine configuration, and local database files. `.env.example` contains placeholders only.
- Python virtual environment `ml/.venv` (9,270 paths in the base snapshot), caches, compiled files, and installed packages. Recreate an environment from dependency files.
- All audio recordings: 58 files, approximately 897,827,189 bytes. Their privacy, licensing/source terms, and suitability for redistribution have not been cleared. No recording or generated substitute is included.
- Seven non-example metadata/mapping CSVs pending privacy/source review: `ml/data/experimental_demo/metadata/classroom_metadata.csv`, `classroom_recording_log.csv`; and `ml/data/metadata/classroom_metadata.csv`, `classroom_recording_log.csv`, `downloaded_audio_inventory.csv`, `experimental_candidate_mapping.csv`, `experimental_selected_file_mapping.csv`.
- Local PostgreSQL database contents and any machine-specific serial/COM settings.

Included data is limited to two dataset manifests, two schema/example CSVs, and empty `.gitkeep` placeholders. The existing trained model artifacts under `ml/artifacts/` are included unchanged and are inventoried by checksum in `SONIQ_COMPLETE_HANDOFF_MANIFEST.md`.

The handoff is a working source snapshot; the excluded data and machine services must be provisioned independently. Do not interpret dataset manifests as the presence of the audio they describe.
