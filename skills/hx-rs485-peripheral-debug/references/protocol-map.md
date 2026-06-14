# HX RS485 protocol map

## Current code scope

Current file:

- `barrier_gate_system/routes/barrier/hxPeripheralRs485.js`

Currently implemented profiles:

- `rs485_4x4_mono`
- `rs485_4x4_fullcolor`

Currently reserved but not implemented:

- `rs485_standard_screen`
- `rs485_2x8_vertical`

Do not claim these reserved profiles are supported unless you implement and verify them.

## Current frame format

Current code builds the packet as:

- header: `AA 55`
- sequence
- address
- reserve `00`
- command
- length high byte
- length low byte
- payload
- CRC16
- end byte `AF`

This matches the vendor protocol docs currently used by HX RS485 support.

## Vendor-package crosswalk

Vendor package:

- vendor RS485 package folder under the workspace, dated `20250423`

Relevant docs:

- the 4x4 horizontal or small-vertical serial protocol PDF
  - aligns with current `rs485_4x4_mono`
- the 4x4 fullcolor serial protocol PDF
  - aligns with current `rs485_4x4_fullcolor`
- the 2x8 standard-vertical serial protocol PDF
  - present in the vendor package but not currently implemented in code
- the voice catalog PDF
  - phrase and token reference for card-based voice
- the SYN6658 plate-broadcast PDF
  - useful when debugging or extending a universal voice module path, but this is not the current default command surface in HX middleware

## Verified vendor protocol details

Verified from the package:

- default serial parameters: `9600 8N1`
- default device address: `100`
- max packet length: `255` bytes
- byte gap requirement: within `10ms`
- ad and config style commands need at least `50ms` before the next command

Vendor commands relevant to current code:

- `0x21` clear temporary display
- `0x22` immediate voice playback
- `0x25` mono ad or idle content
- `0x27` mono temporary display
- `0x35` fullcolor ad or idle content
- `0x37` fullcolor temporary display

Vendor commands present but not currently surfaced in code:

- `0x29` four-line simultaneous temporary display
  - vendor docs themselves describe it as more complex and easier to get wrong
- `0x32` cached voice queue
  - current code uses immediate `0x22`, not queued playback
- config and modify commands such as `0xF0`, `0xF2`, `0xF3`, `0xF4`, `0xF5`, `0xF6`, `0xF7`, `0xF8`

## Current action mapping

- `buildShowCommands`
  - mono -> `0x27`
  - fullcolor -> `0x37`
- `buildIdleCommands`
  - mono -> `0x25`
  - fullcolor -> `0x35`
  - current code adds `delayAfterMs = 50`
- `buildClearCommands`
  - `0x21`
- `buildVoiceCommands`
  - `0x22`
- `buildRemainingCommands`
  - same ad or idle family as idle display
  - current code also adds `delayAfterMs = 50`

## Current text and voice assumptions

- display text is GBK-encoded and capped at `60` bytes per line in current code
- current code supports up to `4` lines
- current voice path is token-based, not arbitrary free text
- unsupported tokens should raise an error instead of being silently passed through
