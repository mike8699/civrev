// Kernel exports the game imports but ReXGlue v0.8.0 does not provide.
// Semantics copied from Xenia (the verification oracle), which boots this game:
//
//   XUsbcamCreate MUST return 0 (X_STATUS_SUCCESS) — Xenia's shim documents
//   that returning an error makes some titles abort init (Carcassonne) and
//   crash later; success + GetState()==0 ("not connected") is the safe pair.
//   The remaining XUsbcam entries are unimplemented in Xenia too (its import
//   dump marks them !!), so plain logging stubs returning 0 match the oracle.
//
// Xbox Live Vision camera support is irrelevant to CivRev gameplay.

#include <rex/hook.h>

REX_EXPORT_STUB_RETURN(__imp__XUsbcamCreate, 0)          // X_STATUS_SUCCESS
REX_EXPORT_STUB_RETURN(__imp__XUsbcamGetState, 0)        // 0 = not connected
REX_EXPORT_STUB_RETURN(__imp__XUsbcamDestroy, 0)
REX_EXPORT_STUB_RETURN(__imp__XUsbcamSetConfig, 0)
REX_EXPORT_STUB_RETURN(__imp__XUsbcamSetCaptureMode, 0)
REX_EXPORT_STUB_RETURN(__imp__XUsbcamReadFrame, 0)
