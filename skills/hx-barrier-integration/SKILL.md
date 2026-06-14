---
name: "hx-barrier-integration"
description: "Use when working on the current HX MQTT barrier integration in `barrier_gate_system` and `cpw_service`, including entry or exit flow changes, topic and device binding checks, image upload handling, message or order tracing, or reconciling older HX docs against the current code."
---

# HX Barrier Integration

Use this skill when the task is about the current HX production flow, not older design drafts. It is for code changes, incident triage, device bring-up, and simulator or real-device verification around the HX MQTT integration.

## Source of truth

Read these in this order:

1. `barrier_gate_system/routes/barrier/hxBarrierInOrder.js`
2. `barrier_gate_system/routes/barrier/indexOut.js`
3. `current HX production-boundary doc under the workspace docs folder`
4. Older HX docs only for history

Important:

- Trust the current code over older HX docs and root-level snapshot files.
- Older HX drafts may still say entry uses `/barrier/parking`. The current code uses `/barrier/beforeParking/self`.

## Quick workflow

1. Confirm the platform target.
   - HX is currently aligned to `cpw_service`.
   - HX platform URL resolves from `config.url.cpw`, then falls back to `config.url.main`.
2. Confirm MQTT identity before reading business logic.
   - The middleware parses `deviceNo` from the topic `/device/{camId}/update` or `/device/{camId}/will`.
   - A correct payload `devId` does not save a bad topic. If the topic contains `{camId}` literally, the device binding will fail.
3. Confirm the current main flow.
   - Entry: `plateResult(in) -> /barrier/beforeParking/self`
   - Exit pre-check: `plateResult(out) -> /barrier/beforeAway/self`
   - Exit close: `barrierStatus(closeEnd) -> /barrier/away/self`
   - Manual or paid release: `/payNotify` and `/barrierStatusNotify` drive `ioOutput`
4. Confirm platform-led control behavior.
   - `open_code=1` triggers gate open.
   - `led_content` triggers screen handling.
   - `broadcast_content` triggers voice handling.
   - These control actions are best-effort and should not erase a successful order flow by themselves.
5. Confirm image handling.
   - `fullPic` or `platePic` stays `base64` with `imageType=base64`.
   - `fullPicPath` or `platePicPath` is converted to `http://{devIp}{path}` with `imageType=url`.
   - If the platform shows no picture, verify the middleware is not sending a path while the platform still assumes base64.
6. Confirm the device and parking binding before blaming code.
   - `parking_device_list.device_no`
   - `parking_lot.interface.hx.parkId`
   - `parking_lot.interface.hx.devices`
   - topic and `camId`
7. Use the simulator only after the live binding is proven.
   - Local simulator config often lags behind the actual parking lot or device binding.
8. If the issue is external display, voice, or remaining spaces over serial, switch to `hx-rs485-peripheral-debug`.

## What this skill is good for

- Reconciling current HX behavior with older docs
- Tracing why entry, exit, pay-notify, or close-end did not complete
- Checking whether a problem is platform-side, middleware-side, or device topic/config-side
- Verifying why pictures are missing even though orders succeeded
- Confirming whether a requested behavior already exists in HX current code

## Validation checklist

- Verify the route and business path in code before changing docs.
- Verify real device identity from MQTT topic before changing parking bindings.
- Verify at least one of:
  - `message_list`
  - `order_list`
  - CPW `barrier_log`
  - current test route output
- When a flow is supposed to be platform-led, check the `self` interface response before changing device behavior.
- When you change the integration, re-run either the HX simulators or the real-device flow and compare logs on both sides.

## References

Load [references/current-verified-boundary.md](references/current-verified-boundary.md) for the current verified HX boundary and file map.

Load [references/live-debug-checklist.md](references/live-debug-checklist.md) for the common production checks, especially topic binding, parking-lot binding, image handling, and cross-service order tracing.
