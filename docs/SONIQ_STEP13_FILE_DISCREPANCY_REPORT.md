# SONIQ Step 13 File Discrepancy Report

Comparison baseline: 120 unique payload paths in the recovered handoff manifest. All missing payloads exist in the recovered Git snapshot. Detailed path-only inventory of all PC-49 files outside the 121-file handoff tree is in SONIQ_STEP13_PC49_ONLY_FILES.csv (the .git database is excluded; no file contents are included).

## Manifest paths absent from PC-49 (40)

| Path | Expected bytes | Expected SHA-256 | Snapshot | Recommended treatment |
|---|---:|---|---|---|
| `backend/start_backend.py` (Source code) | 2799 | `6cd1771646fed86154f07a294279c2db0bac6b96f20aa02983904a6a7b3ab6e2` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `docs/LAN_CONNECTIVITY.md` (Documentation) | 3672 | `10b6ce3e4acaf446964f79a1d639fd612a904cfe2fa4f1026b95d66e96f4e511` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `docs/USB_SERIAL_AUDIO_PROTOCOL.md` (Documentation) | 5436 | `d3d6f4d072d82800aed39e9a7b6c2ff8a5c78a79ec0928c01776fd7971d1d255` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_AUDIT_REPORT.md` (Documentation) | 11053 | `774c850e06dbce80e18814d05e3b9463aaba909ea48d815ce4081cf531d1dbb9` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_COMPLETE_HANDOFF_PUBLISH_PLAN.md` (Documentation) | 4092 | `c3aa2e108b5d3e4e73ca1ebc2689d4e97a6f4f2c812aa07586fc6d65f6d3b4ec` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_DEMO_GUIDE.md` (Documentation) | 7242 | `8784e9d8c090afc614b3b0d4e95eb840b005b1cedc7b2450deac8a2ef05fce1d` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_ACTUAL_TEST_RESULTS.md` (Documentation) | 5814 | `db13a48d09096e2f1ce47e91cc7f38f8c708a908351e4bc3c85afb0d771dcda6` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_BLOCKERS.md` (Documentation) | 4051 | `00547c571004f41796b26001532b4df36426daac013c0a1a38759e55ed837087` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_DEMO_GUIDE.md` (Documentation) | 4701 | `74a5cd186f2dd233b763be8608494391db256a3047c53b4ee633feb6118a64da` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_DEMO_READINESS_REPORT.md` (Documentation) | 16003 | `94e29d90e89188716c7cb24ff3ed401e65f6b9d175579a44b424c87653b04c60` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_DEMONSTRATION_GUIDE.md` (Documentation) | 4303 | `f74df512de943ca7f0a25b7644393fdc898d4003de02f8522cfd23bab42db637` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_INTEGRATION_REPORT.md` (Documentation) | 5676 | `b84f077b8553668bf320afd37aaeed96c4c1ab2de6e901ff983d0db0e6c036db` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_RELEASE_REPORT.md` (Documentation) | 12131 | `60f6136b0e7c525c2c2ba55dfa90a9bfef42509ff12cdd3446ee5a3a73e6cf5a` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_FINAL_REMAINING_BLOCKERS.md` (Documentation) | 3707 | `c3ce6bcc8e3c81d8a7a8249e9901184cf9a375096b297868a8b574f9ff377be3` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_HANDOFF_EXCLUSIONS.md` (Documentation) | 1542 | `f47be6b0476821a21ab543535708c83404755c685728c12b0d05da1ca9752c90` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_INTEGRATION_REPORT.md` (Documentation) | 7375 | `0e838bb2566deb32df585680e8952aec45df2e26c235cd76c76fead2bb2f8c14` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_KNOWN_LIMITATIONS.md` (Documentation) | 4714 | `2a1c97ef438efb86ef6f24222291bb0701f656f7544116ad23e4709894308e24` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_MASTER_COMPLETION_REPORT.md` (Documentation) | 4812 | `2e8be606865df3e6981dba2bacbdde3353d656cbb56da97718cab48195ebb259` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_MASTER_TEST_RESULTS.md` (Documentation) | 5359 | `545ffdfa9360677fc2113e63abdbed4c233a2389effc2e7eb20d45162342e039` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_SECOND_PC_SETUP_GUIDE.md` (Documentation) | 3341 | `8eb8aa87cd17f6b0076f09663505cb9c099026e4f8c10be1b249ad5ac9d71258` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP1_REPORT.md` (Documentation) | 4093 | `1912a05d3ea1d9d6ba00647140553f6fb904a6e425698ec1ac90d25c3fa13aad` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP10_ENVIRONMENT_RECOVERY_REPORT.md` (Documentation) | 10023 | `e3297d362a9deb8f7edbbedddcf04d8a0cd118adf881c5c90041200d911bb887` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP10_REMAINING_BLOCKERS.md` (Documentation) | 7423 | `e93e904349f6523eb419783bbee51df5690a7e19d6b6f53f2f512e9913e98273` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP10_TEST_RESULTS.md` (Documentation) | 10228 | `2344b499a54050cbb05763a09e3ac4d8d8059e9df00b8f52032b631ef5595169` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP2_REPORT.md` (Documentation) | 10031 | `59ff9b0daf6568e7bfbc0e53d0c2c6de57aed5a444c0c4316b174d98c915c5f3` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP3_REPORT.md` (Documentation) | 8078 | `3ede2fcab40596a02fcb698fc3aac05cc4c92522e1a2ac686cd3d89d4507eda7` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP4_REPORT.md` (Documentation) | 6403 | `d9e67ac13a3ef2da4967686e44ea99fb2855aee38a44e1cdb2b5c3ed4e485d47` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP7_BLOCKER_REPORT.md` (Documentation) | 11061 | `7917bb422ed0c778333323c296761d8d9a083201b6acb7bbf5fe9e6d14cb731f` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP7_TEST_RESULTS.md` (Documentation) | 4719 | `0843602bb41901693f3c8dc1039dd519d7c650f9926acd89f5a37791fa973404` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP8_BLOCKER_REPORT.md` (Documentation) | 7545 | `40c9c07a0f7ec52c173316eab3b8b3ab913609e451d6e171ec94b3a7ce13f060` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP8_COMPATIBILITY_REPORT.md` (Documentation) | 8255 | `05426ac323d59a22f6637f3971e6cdf914efda87ddc1128ab80a78b8972ca8b2` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP8_USB_SERIAL_IMPLEMENTATION_PLAN.md` (Documentation) | 17887 | `0c610b5007e46e435c34ec2630c802be8bc683b3d190a80e4631336a83d577a2` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP9_INTEGRATION_REPORT.md` (Documentation) | 7128 | `91886c5a4422c756761b459d3fe68e7956212fce49bad38f5b858ba3f05e1153` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_STEP9_TEST_RESULTS.md` (Documentation) | 5195 | `cbffc415133e3ca3895286d55a9fa2e7a24d21ccc6126a68638ffc7076426770` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_TODAY_DEMO_GUIDE.md` (Documentation) | 8111 | `99d565f3f34e38b1a50fabd266b4461a1057bd364ef33f3a9864deb240b8cf72` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `SONIQ_TODAY_GITHUB_PUBLISH_PLAN.md` (Documentation) | 7696 | `3e86631635c9086c541222a42db4cf77a7439569209017e4fa729ed922031f59` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `start_soniq.bat` (Setup launcher) | 1909 | `623ad5a7e6456a67cd41efdaefa5752530016d23ab37f60c891f3a54139387b2` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `tools/requirements-serial.txt` (Dependency/configuration) | 83 | `d27e5dec2d3c82389b1df79bb88b989ebd2317a66e4ca246fa0459a8a9e97b2a` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `tools/soniq_serial_audio_companion.py` (Source code) | 14975 | `10adec166bf641ea0f752aece7d15b527592f5a352ad659cf374a8fbc0f18aad` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |
| `tools/test_soniq_serial_audio_companion.py` (Source code) | 4591 | `4dbb5689b1d58a078b31f6cd09217f3809779986b28a5dfe6c9ddcd68015a54f` | Present in recovered tree | Include from snapshot only after package-source approval; do not copy into PC-49 |

## Existing PC-49 files with size/hash differences (9)

| Path | Type | Expected bytes / SHA-256 | PC-49 bytes / SHA-256 | Snapshot | Recommended treatment |
|---|---|---|---|---|---|
| `.env.example` (Project file) | 811 / `da101dc8c10eb86ddfe8d759fedd59663cd1512b6ab6a7fee656d4029d604316` | 608 / `3419d2a295d21abeee0fad22b09dd2fe10f923ca2ccb46ff635dc8f63de6df2a` | Present | Keep both variants; package source requires approval |
| `backend/app.py` (Source code) | 32477 / `8a02fbd6856b72125a452d582a453abed28415e67ed9941396270473434fb19d` | 31070 / `83922f56a4f218039b549012c9ab15747d31bd2630413679ed478ba6158183c6` | Present | Keep both variants; package source requires approval |
| `backend/tests/test_app.py` (Source code) | 43272 / `83af4aa151e5334b6843e8bcb5ff7c1cd02b19972ba4ebdb9c9c618ce0444398` | 39229 / `2359f07f01e9a2d230a88c8504dc9fa87436dd7261aff4649e5443ba567ed0db` | Present | Keep both variants; package source requires approval |
| `dashboard/README.md` (Documentation) | 5357 / `224c524a5d730e2c3a4e48919c075ca5fe11f328252e6e7b93215dd188b44508` | 5038 / `4b868fff8f56858791b3dd4f85d2f8584b4e337195bdb399aa27553a6d8ff074` | Present | Keep both variants; package source requires approval |
| `docs/INTEGRATION_PLAN.md` (Documentation) | 4827 / `22252cc2b80170b94115987c4b64277bc0361226a833077adafbc7e6272a5dcf` | 4332 / `db2ba2a5f8217032d22fd273454f8e481b42ae8dcafa5ff8e6a06ad181c37636` | Present | Keep both variants; package source requires approval |
| `docs/INTERFACE_CONTRACT.md` (Documentation) | 12369 / `51caca25a3ff25cbec970c67ce8c807b13175895acd0613406b3c2f2ce8a8095` | 11809 / `7127536771eda03c76a11f5341d2fc32e785112c87cd1779d27742b83537fb55` | Present | Keep both variants; package source requires approval |
| `docs/POSTGRES_LOCAL.md` (Documentation) | 11215 / `65a13d4f20fda52af3b51b9f94388567bf9363802e354ad5c00caebd13d29f0e` | 10729 / `f904ff0ade3dbb1c013f644b52fbe9a125c73f890dee4c071d541b587e2ae660` | Present | Keep both variants; package source requires approval |
| `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino` (Firmware) | 13224 / `39f7d2bd1fb572a8649122cf4ff464be713a50568ecd0e5b6e9d40e5e749eff7` | 13213 / `6877a83158decea403695075c150a36ab92622d2e63810d94e3f61c89c6b1ce0` | Present | Keep both variants; package source requires approval |
| `ml/audio_inference.py` (Source code) | 5425 / `5cd090afa52fc2f0672675aaecb0f30b048ab87adb51eda44748a45345cc2b56` | 5395 / `a0cd0e0338010259b2ca9bdcd683b2352cd8fa34aa37b6c68dd0dbfb1b262f96` | Present | Keep both variants; package source requires approval |

## PC-49-only inventory

The supplemental CSV lists 9359 PC-49-only relative paths at completion (excluding `.git`, including itself, the Step 12/13 reports, local ML virtual environment, and preserved classroom files). It contains names only, not file contents or hashes. Generated audit reports are not source package files.

No missing file was copied; no differing version was replaced. The 40 missing paths are available in the recovered ref; the three manifest conflicts are among the listed absent paths. Approved package source: recovered handoff ref. The package uses its snapshot versions for all 40 absent and nine differing paths; PC-49 counterparts remain unchanged.


