# Skill Market Sync

TokenPort can treat this repository as a registry-backed Skill Market. The sync flow is intentionally file-based so it works with a local clone, GitHub raw files, or a CDN mirror.

## Registry Sources

| Source | Use case |
| --- | --- |
| `market/index.json` in a local clone | Offline or Google Drive synchronized operation |
| `https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json` | Product runtime fetch with CDN and CORS support |
| `https://raw.githubusercontent.com/2508756189/state-of-art-skills/main/market/index.json` | Fallback when jsDelivr is unavailable |

## Build And Validate

```powershell
python scripts\test_build_market.py
python scripts\build_market.py
python scripts\market_sync.py --local market\index.json --remote market\index.json --root . --verify-archives --output summary
```

Expected local checksum result:

```json
{"current": 12}
```

## Diff Statuses

| Status | Meaning | Operator action |
| --- | --- | --- |
| `new` | Skill exists in remote registry but not local registry | Review and import if category/risk is acceptable |
| `upgradable` | Version or archive SHA256 changed | Review changelog/source, then update |
| `current` | Local and remote item match | No action |
| `risk_increased` | Remote risk level is higher than local risk level | Require explicit review before update |
| `checksum_failed` | Archive file is missing or SHA256 does not match registry | Block update and rebuild or re-fetch package |

## Simulated Update Check

Use a copied registry to simulate a remote update without changing market files:

```powershell
python scripts\market_sync.py --local market\index.json --remote <simulated-remote-index.json> --output summary
```

The TokenPort UI should surface the summary first, then allow the operator to inspect item-level details before applying any update.

## TokenPort Integration Notes

- Store the last synced registry, source URL, source commit or timestamp, and item-level archive SHA256.
- Never install every skill automatically; classify and review by category, runtime, and risk level.
- Keep the previous archive until the new package is verified and installed.
- Treat `risk_increased` and `checksum_failed` as review-blocking states.
