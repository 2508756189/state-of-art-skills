# Current verified HX boundary

## Current code locations

- Middleware main flow:
  - `barrier_gate_system/routes/barrier/hxBarrierInOrder.js`
- Platform dispatch:
  - `barrier_gate_system/routes/barrier/indexOut.js`
- Current boundary doc:
  - current HX production-boundary doc in the workspace docs folder

## Current verified flow

- Entry:
  - `plateResult(in) -> /barrier/beforeParking/self`
- Exit pre-check:
  - `plateResult(out) -> /barrier/beforeAway/self`
- Exit completion:
  - `barrierStatus(closeEnd) -> /barrier/away/self`
- Gate open after platform approval:
  - `open_code=1 -> ioOutput`
- Post-payment release:
  - `/payNotify -> ioOutput`

## Current platform-led behavior

The current HX mode follows the ZS-style business boundary:

- Device is responsible for recognition, reporting, receiving commands, and sending responses.
- Platform is responsible for open or not-open decisions, charge decisions, screen text, voice text, and order closure intent.
- Middleware translates platform intent into HX MQTT and RS485 commands.

## Current image handling

`resolveSnapshotPayload` in `hxBarrierInOrder.js` currently behaves like this:

- `fullPic` or `platePic` -> payload snapshot + `imageType=base64`
- `fullPicPath` or `platePicPath` -> `http://{devIp}{path}` + `imageType=url`

If the platform says the order exists but no image appears, this is the first thing to verify.

## Current device capability handling

`getHxDeviceConfig` currently resolves, per device:

- `ioOpenNum`
- `ioCloseNum`
- `supportMlLed`
- `supportLcd`
- `supportTts`
- `supportRs485`
- `peripheralProfile`
- `rs485Channel`
- `rs485Address`
- `voiceProfile`
- `rs485EncodeType`

## Current known pitfalls

- Device identity comes from MQTT topic, not only from payload `devId`.
- Older docs may still say entry is `/barrier/parking`; current code uses `/barrier/beforeParking/self`.
- Root-level snapshot files can drift. Prefer the live repo file under `barrier_gate_system`.
- Platform-led display and voice are best-effort device actions layered on top of a business-successful order flow.
