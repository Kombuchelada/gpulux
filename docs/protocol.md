# LED controller protocol (MSI RTX 40-series)

Interface spec for the RGB controller on the MSI GeForce RTX 40-series cards listed in the README.

## Bus and identity

- **Bus:** the GPU's first I²C port. With the NVIDIA driver on Linux, that's the `/dev/i2c-N` named
  `NVIDIA i2c adapter 1 at <pci address>`.
- **Address:** `0x68` (7-bit).
- **Writes:** `[register, value]`, or `[register, b0, b1, …]` for block registers.
- **Reads:** write `[register]`, then a repeated-start read of N bytes.
- **Timing:** 20 ms between writes.

Identify the controller with two reads (neither changes state):

| Register | Read | Meaning |
|---|---|---|
| `0xEC` | 4 bytes | LED type, module type (big-endian 16-bit), firmware version |
| `0xED` | 2 bytes | chip ID, big-endian |

The tested card (RTX 4070 Ti SUPRIM, `10de:2782` / `1462:5133`) reports LED type 17, module `0x0000`,
firmware 18 and chip `0x8232`. Other registers don't read back meaningfully.

## Registers

| Reg | Use |
|---|---|
| `0x22` | mode (see below); `0x1C` is written first to prepare a mode change |
| `0x27` `0x28` `0x29` | color slots 1–3, 3-byte blocks in **B, G, R** order |
| `0x2D` | zones forced off, as a bitmask: `1` side, `2` front (the LEDs behind the fans), `4` back. `0` = all on |
| `0x30` `0x31` `0x32` | primary color R, G, B |
| `0x36` | brightness in percent: 20, 40, 60, 80, 100 |
| `0x38` | effect period: `4` slow, `2` medium, `1` fast |
| `0x3F` | write `0` to persist the current state across power cycles; wait about 1 s before writing it |
| `0x46` | flags for wave and color-cycle: bit 0 = use custom color slots, bit 1 = reverse direction |

Effects take effect immediately. `0x3F` only controls whether they survive a power cycle.

## Applying an effect

Write `0x2D = 0` (all zones on), then the effect's writes, then optionally `0x3F = 0` after a 1 s pause.

`P` = `0x22 ← 0x1C`, `T` = `0x36 ← brightness`, `0x38 ← period`, and `RGB` = `0x30..0x32 ← R, G, B`.

| Effect | Writes | Final `0x22` |
|---|---|---|
| off | `0x2D ← zone mask` | none |
| static | P, T, RGB | `0x13` |
| flashing | P, T, RGB | `0x02` |
| double-flashing | P, T, RGB | `0x03` |
| patrolling | P, T, RGB | `0x05` |
| marquee | P, T, RGB | `0x18` single color, `0x19` rainbow |
| meteor | P, T, RGB | `0x16` / `0x17` |
| stack | P, T, RGB | `0x0D` / `0x0E` |
| flowing | P, T, RGB | `0x09` / `0x0A` |
| whirling | P, T, RGB | `0x0F` / `0x10` |
| twisting | P, T, RGB | `0x11` / `0x12` |
| rhythm | P, T, RGB | `0x0B` / `0x0C` |
| streaming | P, T | `0x06` |
| lightning | P, T | `0x15` |
| breathing | P, `0x27 ← c1`, `0x28 ← c2`, T | `0x04` |
| fade-in | P, `0x28 ← c1`, `0x27 ← c2`, T | `0x14` |
| wave, rainbow | `0x46 ← 0` (reverse: `2`), T | `0x08` |
| wave, colors | `0x46 ← 1`, P, `0x29 ← c1`, `0x27 ← c2`, `0x28 ← c3`, T | `0x08` |
| wave, colors, reverse | `0x46 ← 3`, P, `0x27 ← c1`, `0x28 ← c2`, `0x29 ← c3`, T | `0x08` |
| color-cycle, rainbow | P, `0x46 ← 0`, T | `0x07` |
| color-cycle, colors | P, `0x46 ← 1`, P, `0x27 ← c1`, `0x28 ← c2`, `0x29 ← c3`, T | `0x07` |
| preset, rainbow | P, T | `0x1E` |
| preset, color | P, T, RGB | `0x1D` |

Zones not in the `off` mask keep running the last effect.

On `10de:2882` / `1462:5164` and `1462:5165` (RTX 4060 GAMING X NV EDITION, GAMING MLG), the preset is a
static color: P, `0x36 ← 80`, `0x38 ← 1`, RGB, `0x22 ← 0x13`.

The set of effects each card offers is in `src/gpulux/cards.py`.

## Observed on hardware

On the RTX 4070 Ti SUPRIM: static color, rainbow wave, and `off` with mask `2`, which darkens only the LEDs
behind the fans. Nothing else in this document has been observed yet.
