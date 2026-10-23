<img src="assets/icon.svg" width="64" height="64" alt="">

# gpulux: RGB lighting control for MSI RTX 40-series cards on Linux

`gpulux` controls the RGB lighting on **MSI GeForce RTX 40-series graphics cards** from Linux. It's an
alternative to MSI Center / Mystic Light, which only run on Windows. It was built for the
**MSI RTX 4070 Ti SUPRIM**. You can set a static color, pick an effect (wave, breathing, rainbow,
marquee, …), or turn the GPU LEDs off, all from the command line.

It talks to the card's LED controller directly over the GPU's I²C bus. The register protocol is documented
in [docs/protocol.md](docs/protocol.md).

> [!WARNING]
> **Only tested on one card: MSI RTX 4070 Ti SUPRIM** (PCI `10de:2782`, subsystem `1462:5133`) with the
> NVIDIA proprietary driver. Even there, only static color, rainbow wave and turning zones off were confirmed
> by eye. The other effects are implemented but haven't been observed. The
> [other cards listed below](#supported-cards) are believed to use the same LED controller, but gpulux hasn't
> been run on any of them. It writes to your GPU's LED controller, so use it at your own risk.
> [Card reports](https://github.com/Kombuchelada/gpulux/issues/new?template=card-report.md) are very welcome.

## Install

Python 3.9+, no dependencies.

```sh
pipx install git+https://github.com/Kombuchelada/gpulux
# or from a checkout: pipx install .
```

You need read/write access to `/dev/i2c-*`:

```sh
sudo modprobe i2c-dev                                        # load now
echo i2c-dev | sudo tee /etc/modules-load.d/i2c-dev.conf     # load at boot
sudo groupadd -f i2c && sudo usermod -aG i2c "$USER"         # then log out and back in
# if /dev/i2c-* isn't group i2c on your distro:
echo 'KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0660"' | sudo tee /etc/udev/rules.d/60-i2c.rules
```

## Usage

```sh
gpulux info                          # find the card, read the controller, list its effects
gpulux off                           # all GPU LEDs off
gpulux off --zones front             # just the fan LEDs (zones: front, side, back)
gpulux static ff0000                 # solid red; colors are RRGGBB or red/green/blue/white/...
gpulux static white -b 2             # brightness 1-5
gpulux breathing blue purple -s slow
gpulux wave                          # rainbow wave (the factory default)
gpulux wave red green blue --reverse
gpulux marquee                       # rainbow; `marquee 00ff80` for a single color
gpulux static cyan --no-save         # don't persist; reverts on power cycle
gpulux static cyan --dry-run         # print the register writes, touch nothing
```

Changes are saved to the card by default, so they survive reboots and need no software running. Pass
`--no-save` for anything that changes often, to avoid wearing the controller's flash.

| Effect | Colors | Effect | Colors |
|---|---|---|---|
| `static` | 1 | `stack` | 1 or rainbow |
| `breathing` | 2 (optional) | `flowing` | 1 or rainbow |
| `flashing` | 1 | `whirling` | 1 or rainbow |
| `double-flashing` | 1 | `twisting` | 1 or rainbow |
| `patrolling` | 1 | `wave` | 3 or rainbow, `--reverse` |
| `marquee` | 1 or rainbow | `color-cycle` | 3 or rainbow |
| `fade-in` | 2 (optional) | `streaming`, `lightning` | none |
| `preset` | 1 or rainbow | `off` | `--zones` |

`gpulux info` shows which of these your card offers. Some cards also have `meteor` and `rhythm`.

## Supported cards

These MSI NVIDIA cards are believed to use the same LED controller. Detection is automatic. Cards that
aren't listed are skipped unless you pass `--force`.

<details>
<summary>51 cards (RTX 4090, 4080 SUPER, 4080, 4070 Ti SUPER, 4070 Ti, 4070 SUPER, 4070, 4060 Ti, 4060)</summary>

| MSI board | GPU | Subsystem | Status |
|---|---|---|---|
| RTX 4090 SUPRIM 24G | `10de:2684` | `1462:5102` | untested |
| RTX 4090 GAMING TRIO 24G | `10de:2684` | `1462:5103` | untested |
| RTX 4090 SUPRIM LIQUID 24G | `10de:2684` | `1462:5104` | untested |
| RTX 4090 SUPRIM CLASSIC | `10de:2684` | `1462:5105` | untested |
| RTX 4090 GAMING TRIO CLASSIC | `10de:2684` | `1462:5106` | untested |
| RTX 4090 GAMING SLIM 24G | `10de:2684` | `1462:510b` | untested |
| RTX 4090 D 24G SUPRIM | `10de:2685` | `1462:5102` | untested |
| RTX 4090 D 24G GAMING SLIM | `10de:2685` | `1462:510b` | untested |
| RTX 4080 SUPER 16G SUPRIM | `10de:2702` | `1462:5110` | untested |
| RTX 4080 SUPER 16G GAMING TRIO | `10de:2702` | `1462:5111` | untested |
| RTX 4080 SUPER 16G GAMING SLIM | `10de:2702` | `1462:5117` | untested |
| RTX 4080 SUPER 16G GAMING SLIM WHITE | `10de:2702` | `1462:511a` | untested |
| RTX 4080 16GB SUPRIM | `10de:2704` | `1462:5110` | untested |
| RTX 4080 16GB GAMING TRIO | `10de:2704` | `1462:5111` | untested |
| RTX 4080 16GB GAMING TRIO WHITE | `10de:2704` | `1462:5115` | untested |
| RTX 4080 16GB GAMING SLIM | `10de:2704` | `1462:5117` | untested |
| RTX 4080 16GB GAMING SLIM WHITE | `10de:2704` | `1462:511a` | untested |
| RTX 4070 Ti SUPER 16G GAMING TRIO WHITE | `10de:2705` | `1462:5139` | untested |
| RTX 4070 Ti SUPER 16G GAMING SLIM | `10de:2705` | `1462:e130` | untested |
| RTX 4070 Ti SUPER 16G GAMING SLIM WHITE | `10de:2705` | `1462:e132` | untested |
| RTX 4070 Ti SUPER 16G GAMING SLIM STALKER 2 EDITION | `10de:2705` | `1462:e133` | untested |
| RTX 4070 Ti SUPER 16G GAMING SLIM | `10de:2705` | `1462:e13d` | untested |
| RTX 4070 Ti SUPER 16G GAMING SLIM WHITE | `10de:2705` | `1462:e13e` | untested |
| RTX 4070 Ti GAMING TRIO | `10de:2782` | `1462:5132` | untested |
| RTX 4070 Ti SUPRIM | `10de:2782` | `1462:5133` | ✅ tested |
| RTX 4070 Ti GAMING TRIO WHITE | `10de:2782` | `1462:5139` | untested |
| RTX 4070 TI GAMING SLIM | `10de:2782` | `1462:e130` | untested |
| RTX 4070 Ti GAMING SLIM WHITE | `10de:2782` | `1462:e132` | untested |
| RTX 4070 SUPER 12G GAMING SLIM | `10de:2783` | `1462:513f` | untested |
| RTX 4070 SUPER 12G GAMING SLIM WUKONG EDITION | `10de:2783` | `1462:51c0` | untested |
| RTX 4070 SUPER 12G GAMING SLIM WHITE | `10de:2783` | `1462:e131` | untested |
| RTX 4070 SUPER 12G GAMING SLIM MLG | `10de:2783` | `1462:e134` | untested |
| RTX 4070 SUPER 12G GAMING SLIM World of Warcraft EDITION | `10de:2783` | `1462:e13f` | untested |
| RTX 4070 GAMING TRIO | `10de:2786` | `1462:5136` | untested |
| RTX 4070 GAMING SLIM | `10de:2786` | `1462:513f` | untested |
| RTX 4070 GAMING SLIM WHITE | `10de:2786` | `1462:e131` | untested |
| RTX 4060 Ti GAMING TRIO 8G | `10de:2803` | `1462:5151` | untested |
| RTX 4060 Ti GAMING 8G | `10de:2803` | `1462:5152` | untested |
| RTX 4060 Ti GAMING SLIM WHITE 8G | `10de:2803` | `1462:5156` | untested |
| RTX 4060 Ti GAMING SLIM 8G | `10de:2803` | `1462:5157` | untested |
| RTX 4060 Ti 8G GAMING SLIM MH EDITION | `10de:2803` | `1462:5158` | untested |
| RTX 4060 Ti GAMING SLIM 16G | `10de:2803` | `1462:5170` | untested |
| RTX 4060 Ti GAMING SLIM WHITE 16G | `10de:2803` | `1462:5171` | untested |
| RTX 4060 Ti GAMING 16G | `10de:2803` | `1462:5172` | untested |
| RTX 4060 Ti GAMING SLIM 16G | `10de:2805` | `1462:5170` | untested |
| RTX 4060 Ti GAMING SLIM WHITE 16G | `10de:2805` | `1462:5171` | untested |
| RTX 4060 Ti GAMING 16G | `10de:2805` | `1462:5172` | untested |
| RTX 4060 (AD106) | `10de:2808` | `1462:5160` | untested |
| RTX 4060 GAMING | `10de:2882` | `1462:5160` | untested |
| RTX 4060 GAMING X NV EDITION | `10de:2882` | `1462:5164` | untested |
| RTX 4060 GAMING MLG | `10de:2882` | `1462:5165` | untested |

</details>

AMD cards aren't supported, and neither are MSI's RTX 20, 30 or 50-series cards, which use different LED
controllers.

## Troubleshooting

- **`permission denied`**: see the `i2c` group setup above.
- **`not found`**: `sudo modprobe i2c-dev`.
- **`no LED controller answered`**: the card is listed, but nothing replied at `0x68` on any of its I²C
  adapters. Only the NVIDIA proprietary driver has been tried. Please open a card report with
  `gpulux info --force` and `i2cdetect -l` output.
- **Lights reset after reboot**: you used `--no-save`.

## How it works

The NVIDIA driver exposes each GPU's I²C ports as `/dev/i2c-N` ("NVIDIA i2c adapter N"). The LED controller
is at address `0x68` on adapter 1. An effect is a short sequence of register writes (mode, color, brightness,
speed), followed by an optional save. Full register map: [docs/protocol.md](docs/protocol.md).

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Disclaimer

gpulux is an independent project. It isn't affiliated with or endorsed by Micro-Star International (MSI)
or NVIDIA. MSI, Mystic Light, MSI Center, SUPRIM, GeForce and RTX are trademarks of their respective
owners, used here only to describe compatibility. No warranty ([MIT](LICENSE)); use at your own risk.
