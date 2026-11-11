# SONIQ Step 11 Dataset Inventory

Inspected $((Get-Location).Path)\ml\data on 2026-11-10.

- 69 non-placeholder files: 58 audio recordings (43 WAV, 9 MP3, 2 AIFF, 2 FLAC, 2 M4A) plus 11 CSV/JSON metadata and manifest files.
- Total source size: 897,952,250 bytes (about 856.4 MiB / 0.836 GiB).
- Dataset structure includes classroom_collection/audio/recordings, experimental_demo/audio/recordings and metadata, expanded_local_demo_20261020/audio/recordings, and root metadata.
- Metadata includes classroom metadata and recording logs, downloaded audio inventory, experimental candidate and selected-file mappings, and dataset manifests. Training scripts/configs reference dataset roots; ml/config/first-baseline.json points to ../data/classroom_collection.
- 9 groups contain byte-identical files (including copies in demo subsets). All copies are retained in the archive. This detects identical content, not mistaken labels.
- No source file was moved or changed. Completeness against the absent PC-21 original cannot be assessed.
