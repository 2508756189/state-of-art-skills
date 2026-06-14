# Live debug checklist

## 1. Confirm the device identity path first

HX currently parses the device number from the MQTT topic:

- expected publish topic: `/device/{real-camId}/update`
- expected will topic: `/device/{real-camId}/will`
- expected subscribe topic: `/device/{real-camId}/get`

If the device uses `/device/{camId}/update` literally, the middleware records `device_no = {camId}` and binding fails even if payload `devId` is correct.

## 2. Confirm parking and device binding

Check these together:

- middleware `parking_device_list.device_no`
- middleware `parking_device_list.parking_lot_no`
- middleware `parking_lot.interface.hx.parkId`
- middleware `parking_lot.interface.hx.devices`
- CPW side port binding if a platform order is involved

Do this before changing code.

## 3. Confirm current flow expectation

- Entry should hit `/barrier/beforeParking/self`
- Exit should hit `/barrier/beforeAway/self`
- `closeEnd` should hit `/barrier/away/self`
- `payNotify` and `barrierStatusNotify` should drive `ioOutput`

If a report says "no open command was sent", check whether:

- entry flow currently returns `open_code=1`
- exit flow returned `open_code=0` because payment is still uncleared

## 4. Confirm picture mode

If the device sends image paths instead of base64:

- middleware must send `imageType=url`
- the URL must be reachable from the platform side

If the order is fine but no image is visible, compare:

- raw HX message payload
- transformed middleware request to CPW
- platform-side image save behavior

## 5. Confirm cross-service evidence

When chasing a live incident, compare at least:

- middleware `message_list`
- middleware `order_list`
- CPW order table
- CPW `barrier_log`

Do not trust only one side.

## 6. When to hand off to the RS485 skill

Switch to `hx-rs485-peripheral-debug` when the business flow is already correct and the remaining problem is one of:

- screen content not displayed
- voice not played
- remaining spaces not shown
- `rs485TransmitRsp=ok` but the physical peripheral does nothing
