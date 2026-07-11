# SDK defects found / local patches carried

Pinned SDK: rexglue-sdk v0.8.0 (`2bdb97f`). Every entry lists symptom, root
cause, our carry, and upstream status — so version bumps are auditable.

## 1. Conditional tail call loses CallTarget under overlapping coverage

- **Symptom:** generated code contains
  `if (...) REX_FATAL("Unresolved branch from 0x823E5948 to 0x823E5854")`
  (3 sites in CivRev) although the target address IS a registered function;
  codegen logs `Unresolved conditional branch ... (no CallTarget)`. At
  runtime the game dies at the first such site during boot.
- **Trigger:** a `[functions]` hint for a data-referenced entry (e.g.
  0x823E5880) that lies INSIDE another function's range (0x823E5840). Both
  functions translate the same bytes; `findCallTarget(site)` is keyed by site
  address and only carries the resolution for one copy.
- **Local patch:** `src/codegen/builders/context.cpp`,
  `emit_conditional_branch`: when `findCallTarget(base)` misses but
  `graph().getFunction(target)` exists, emit the conditional tail call
  directly (same shape as the CallTarget::isFunction branch). Patch is
  additive fallback only — no behavior change when CallTarget resolves.
- **Upstream status:** not filed yet (prepare reproducer once boot is green;
  minimal repro = two overlapping [functions] entries where the inner one
  conditionally branches below its own entry).

## 2. XUsbcam* exports missing (not a bug — gap)

- v0.8.0 has no XUsbcam* xboxkrnl exports; CivRev imports 6 of them and they
  are link-time-required by generated code. Carried as app-side stubs in
  `civrev/src/kernel_stubs.cpp` (Xenia semantics: Create MUST return success).
  Candidate for upstreaming as SDK stubs.
