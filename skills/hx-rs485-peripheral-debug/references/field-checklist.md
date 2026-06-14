# HX RS485 field checklist

## When to use this checklist

Use this checklist when:

- `rs485TransmitRsp` returns `status=ok`
- middleware logs show the command was sent
- but the external display or voice still does nothing on site

## What `ok` means

`ok` means the camera accepted and forwarded the serial command.

It does not prove:

- the peripheral address matched
- the command family matched the actual screen model
- the external display showed anything
- the voice board played anything

## First-pass field checks

Check these before changing middleware code:

- RS485 channel matches the physical wiring
  - current middleware supports channel `1` or `2`
- RS485 address matches the physical peripheral
  - middleware default assumption is `100`
- baud rate matches on both sides
  - vendor default is `9600`
- parity and stop bits match on both sides
  - vendor default is `8N1`
- A/B wiring is correct
- peripheral has power
- protocol profile matches the actual screen type

## Profile selection checks

Current code only implements:

- `rs485_4x4_mono`
- `rs485_4x4_fullcolor`

If the site uses:

- standard horizontal card
- 2x8 vertical card
- another vendor card

do not assume a config tweak is enough. The profile may need real code support.

## Common misdiagnoses

- "The middleware is wrong because the screen did not light up"
  - first verify address, channel, wiring, and profile
- "The camera replied ok, so the peripheral must be fine"
  - camera success only proves the RS485 transmit step, not the final hardware effect
- "The protocol package contains a command, so the current middleware must support it"
  - verify the command is actually implemented in `hxPeripheralRs485.js`

## Recommended test order

1. Clear the screen
2. Send one short temporary display line
3. Send one short idle display line
4. Send one fixed voice phrase from the known token catalog
5. Only then try remaining-space or multi-step business text

If step 2 already fails on site while the camera returns `ok`, this is usually hardware or field config, not business logic.
