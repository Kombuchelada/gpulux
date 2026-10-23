import argparse
import errno
import sys
import time

from . import __version__, devices, protocol
from .i2c import I2CBus

NAMED_COLORS = {
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255), "white": (255, 255, 255),
    "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255), "purple": (128, 0, 255),
    "orange": (255, 96, 0), "pink": (255, 64, 160),
}
SPEEDS = {"slow": 1, "medium": 2, "fast": 3}
ZONES = {"side": protocol.ZONE_SIDE, "front": protocol.ZONE_FRONT, "back": protocol.ZONE_BACK}


def parse_color(text):
    t = text.lower().lstrip("#")
    if t in NAMED_COLORS:
        return NAMED_COLORS[t]
    if len(t) == 6:
        try:
            return tuple(bytes.fromhex(t))
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(f"bad color {text!r} (use RRGGBB or one of: {', '.join(NAMED_COLORS)})")


def parse_speed(text):
    if text in SPEEDS:
        return SPEEDS[text]
    if text in ("1", "2", "3"):
        return int(text)
    raise argparse.ArgumentTypeError("speed is slow|medium|fast or 1..3")


def parse_zones(text):
    mask = 0
    for z in text.split(","):
        if z not in ZONES:
            raise argparse.ArgumentTypeError(f"zones are {','.join(ZONES)}")
        mask |= ZONES[z]
    return mask


def make_parser():
    effects = "\n".join(f"  {e.name:<16} {e.help}" + (f"  [{e.colors} color{'s' * (e.colors > 1)}]" if e.colors else "")
                        for e in protocol.EFFECTS.values())
    p = argparse.ArgumentParser(
        prog="gpulux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Control the RGB lighting on MSI RTX 40-series graphics cards.",
        epilog=f"commands:\n  {'info':<16} detect cards and read the LED controller\n\neffects:\n{effects}\n\n"
               "Effects that support rainbow use it when no color is given.",
    )
    p.add_argument("command", help="info, or an effect name")
    p.add_argument("colors", nargs="*", type=parse_color, metavar="COLOR", help="RRGGBB or a color name")
    p.add_argument("-b", "--brightness", type=int, default=5, choices=range(1, 6), metavar="1-5", help="default 5")
    p.add_argument("-s", "--speed", type=parse_speed, default=2, metavar="SPEED", help="slow|medium|fast (default medium)")
    p.add_argument("--reverse", action="store_true", help="wave: reverse direction")
    p.add_argument("--zones", type=parse_zones, default=protocol.ALL_ZONES, metavar="LIST",
                   help="off: comma list of front (fan LEDs), side, back (default all)")
    p.add_argument("--no-save", dest="save", action="store_false",
                   help="don't persist to the controller (reverts on power cycle; avoids flash writes)")
    p.add_argument("--bus", type=int, help="use /dev/i2c-N instead of auto-detecting")
    p.add_argument("--force", action="store_true", help="allow cards and effects not in the supported-card table")
    p.add_argument("--dry-run", action="store_true", help="print the register writes instead of sending them")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def find_targets(args):
    """Return [(bus_number, card)] of reachable controllers."""
    if args.bus is not None:
        card = next((c for _, c, buses in devices.find_gpus() if any(b == args.bus for b, _ in buses)), None)
        return [(args.bus, card)]
    targets = []
    for pci, card, buses in devices.find_gpus():
        if card not in devices.CARDS and not args.force:
            print(f"{pci}: {devices.card_label(card)} isn't in the supported-card table; skipping (--force to try)",
                  file=sys.stderr)
            continue
        for bus, _name in devices.port_order(buses):
            try:
                with I2CBus(bus) as b:
                    protocol.read_info(b)
            except OSError as e:
                if e.errno in (errno.EACCES, errno.EPERM, errno.ENOENT):
                    raise
                continue
            targets.append((bus, card))
            break
        else:
            print(f"{pci}: no LED controller answered at 0x{protocol.ADDR:02x}", file=sys.stderr)
    return targets


def cmd_info(targets):
    for bus, card in targets:
        with I2CBus(bus) as b:
            info = protocol.read_info(b)
        effects = devices.supported_effects(card)
        tested = "tested" if card in devices.TESTED else "untested"
        label = devices.card_label(card) if card else "unknown card"
        print(f"{devices.card_name(card)} ({label}, {tested})")
        print(f"  /dev/i2c-{bus} addr 0x{protocol.ADDR:02x}  chip 0x{info['chip_id']:04x}  led-type {info['led_type']}  "
              f"module 0x{info['module_type']:04x}  fw {info['fw_version']}")
        print(f"  effects: {' '.join(effects) if effects else 'unknown (not in the supported-card table)'}")


def build_ops(args, card):
    effect = protocol.EFFECTS.get(args.command)
    if effect is None:
        raise SystemExit(f"unknown command {args.command!r}; see --help")
    supported = devices.supported_effects(card)
    if supported is not None and effect.name not in supported and not args.force:
        raise SystemExit(f"{devices.card_name(card)} doesn't offer '{effect.name}'. "
                         f"Supported: {' '.join(supported)} (--force to try)")
    n = len(args.colors)
    if n > effect.colors or (effect.colors == 1 and n == 0 and not effect.rainbow):
        raise SystemExit(f"{effect.name} takes {effect.colors} color(s), got {n}")
    if effect.colors > 1 and n not in (0, effect.colors):
        raise SystemExit(f"{effect.name} takes {effect.colors} colors (or none for the defaults), got {n}")
    rainbow = effect.rainbow and n == 0
    return protocol.build(effect.name, args.colors, rainbow=rainbow, reverse=args.reverse, brightness=args.brightness,
                      speed=args.speed, zones=args.zones, card=card, save=args.save)


def main(argv=None):
    args = make_parser().parse_args(argv)
    if args.command != "info" and args.command not in protocol.EFFECTS:
        raise SystemExit(f"unknown command {args.command!r}; see --help")
    if args.dry_run and args.command != "info":
        card = next((c for _, c, _ in devices.find_gpus()), None)
        for op in build_ops(args, card):
            print(f"sleep {op.ms} ms" if isinstance(op, protocol.Sleep) else f"0x{op.reg:02x} <- {op.data.hex(' ')}")
        return 0
    try:
        targets = find_targets(args)
        if not targets:
            raise SystemExit("no supported GPU LED controller found")
        if args.command == "info":
            cmd_info(targets)
            return 0
        for bus, card in targets:
            ops = build_ops(args, card)
            if card not in devices.TESTED:
                print(f"note: {devices.card_name(card)} is untested with gpulux; please report how it went",
                      file=sys.stderr)
            with I2CBus(bus) as b:
                protocol.run(b, ops, time.sleep)
    except PermissionError as e:
        raise SystemExit(f"{e.filename}: permission denied. Add yourself to the i2c group (or run as root).")
    except FileNotFoundError as e:
        raise SystemExit(f"{e.filename}: not found. Load the i2c-dev module: sudo modprobe i2c-dev")
    except OSError as e:
        raise SystemExit(f"I2C error: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
