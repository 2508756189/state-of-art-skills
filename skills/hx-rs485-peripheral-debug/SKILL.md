---
name: "hx-rs485-peripheral-debug"
description: "Use when debugging or extending HX RS485-based external display, voice, or remaining-space control, especially around `hxPeripheralRs485.js`, `rs485Transmit`, vendor protocol compatibility, or cases where the camera reports success but the physical screen or voice module does not react."
---

# HX RS485 Peripheral Debug

Use this skill when the problem is no longer the HX order flow itself, but the external display or voice execution path behind the camera.

## Source of truth

Read these in this order:

1. `D:\华夏相机对接\barrier_gate_system\routes\barrier\hxPeripheralRs485.js`
2. `D:\华夏相机对接\barrier_gate_system\routes\barrier\hxBarrierInOrder.js`
3. Vendor package `D:\华夏相机对接\中性 车牌识别显示卡 对接包 20250423`
4. On-site camera and peripheral configuration

If those local files or vendor documents are unreadable because of Windows path, encoding, or `rg` execution issues, use `ai-read-fix` before proceeding.

## Quick workflow

1. Confirm the failure boundary.
   - If the business order failed, use `hx-barrier-integration` first.
   - If the business order succeeded but the screen or voice did not react, stay in this skill.
2. Confirm per-device capability and profile.
   - `supportRs485`
   - `peripheralProfile`
   - `rs485Channel`
   - `rs485Address`
   - `rs485EncodeType`
   - `voiceProfile`
3. Confirm whether the requested profile is actually implemented.
   - Implemented: `rs485_4x4_mono`, `rs485_4x4_fullcolor`
   - Reserved and not implemented: `rs485_standard_screen`, `rs485_2x8_vertical`
4. Map the action to the current command family.
   - temporary display -> mono `0x27`, fullcolor `0x37`
   - idle or ad display -> mono `0x25`, fullcolor `0x35`
   - clear temporary display -> `0x21`
   - voice -> `0x22`
   - remaining spaces -> current code reuses the idle or ad family with 50ms spacing
5. Check vendor guardrails before changing code.
   - default serial parameters: `9600 8N1`
   - default address: `100`
   - packet max length: `255` bytes
   - byte-to-byte gap: keep within `10ms`
   - after ad or config style commands, wait at least `50ms` before the next command
6. Interpret responses correctly.
   - `rs485TransmitRsp status=ok` proves the camera accepted and forwarded the serial command.
   - It does not prove the external screen displayed or the voice board actually spoke.
7. If the camera says `ok` but the peripheral is silent, check hardware and field config before rewriting protocol code.
   - RS485 channel
   - RS485 address
   - A/B wiring
   - peripheral power
   - protocol model
   - baud rate and parity on both sides
8. When changing voice behavior, compare against the vendor voice catalog.
   - current code supports fixed phrase tokens, ASCII digits and letters, and a limited GBK single-character set
   - unsupported text should fail loudly instead of silently mutating

## What this skill is good for

- Debugging why screen or voice control does not show up on site
- Extending `hxPeripheralRs485.js`
- Verifying whether a new peripheral profile needs real implementation or only config changes
- Explaining why a camera-side success response is not enough to prove a hardware result

## Validation checklist

- Compare the intended action against the implemented profile list before adding new config.
- Compare the generated command family against the vendor protocol doc before changing bytes.
- Confirm the on-site RS485 settings match middleware assumptions before changing command payloads.
- When updating token maps or phrase support, test at least one known-good phrase and one expected failure phrase.

## References

Load [references/protocol-map.md](references/protocol-map.md) for the current protocol mapping, implemented command families, and vendor-package crosswalk.

Load [references/field-checklist.md](references/field-checklist.md) for the on-site checks to run when the camera returns `ok` but the physical screen or voice output is still wrong.
