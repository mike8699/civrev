# CivRev ReXGlue port — progress journal

Read `../REXGLUE_PORT_PRD.md` first; this file assumes it. Newest session at top.

## Session 1 — 2026-07-11 — M0 (toolchain) → M1 (codegen)

**Session goal:** boot the port far enough that the opening copyright/legal
screens render correctly (PRD M0→M4-partial).

### Done
- Branch `rexglue-port` created off `xenia-oracle-harness`.
- `.gitignore` written BEFORE anything else (excludes `civrev/generated/`,
  SDK checkout/install, zips, logs, all game-file extensions).
- ReXGlue SDK v0.8.0: cloned at tag `2bdb97f` (`rexglue-sdk/`, gitignored) AND
  prebuilt linux-amd64 release binary downloaded → `sdk_install/linux-amd64/`
  (gitignored). Prebuilt `rexglue --help` works on host. Rationale: prebuilt
  CLI unblocks codegen immediately; the source checkout is for local patches
  if needed (troubleshooting playbook) and is built via Docker.
- `docker/Dockerfile.toolchain` — replicates the SDK's own linux-amd64 CI env
  (ubuntu 24.04 + clang-20 + LunarG vulkan-sdk + GTK3 + audio deps + Xvfb/
  lavapipe/tesseract for headless port runs). Image `rexglue-toolchain`
  (build in progress).
- Scaffolded `civrev/` via
  `rexglue init --project-name civrev --xex-path ../xenon_recomp/work/extracted/default.xex --game-root ../xenon_recomp/work/extracted --project-root ./civrev`.
  NOTE: v0.8.0 CLI flags differ from PRD §5 sketch (`--app_name` → `--project-name`
  etc.); manifest file is `civrev_manifest.toml` (not `civrev_config.toml`),
  sections `[project]` + `[entrypoint]`. Config field names verified against
  `src/codegen/config.cpp` — match PRD §5 list (`[functions]`,
  `[[switch_tables]]` with address/register/labels, `[[invalid_instructions]]`,
  `[[midasm_hook]]`, `[rexcrt]`, `setjmp`/`longjmp`, `[analysis]`).
- Known harness fact: `references/boot/` bundle is STALE (checkpoint names from
  an older boot script, status=crash, screenshot shows profile dialog —
  predates profile seeding). Needs recapture before M3/M4 comparisons.

### In flight
- First `rexglue codegen` run (no `--force`) — collecting validation errors.
- Docker toolchain image build.

### Next
- M1: iterate codegen to exit 0 without `--force`; sanity-check function count
  vs XenonRecomp's 63,266.
- Recapture `references/boot` (take GPU lock; verify legal-screen checkpoint
  present and non-crashed).
- M2: build port in `rexglue-toolchain` container.
