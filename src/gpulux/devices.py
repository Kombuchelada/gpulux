"""Supported cards and bus discovery."""

import glob
import os

from .cards import CARDS, CORE
from .protocol import EFFECTS

TESTED = {(0x2782, 0x5133)}  # RTX 4070 Ti SUPRIM


def card_label(card):
    device, subsystem = card
    return f"10de:{device:04x} 1462:{subsystem:04x}"


def card_name(card):
    return CARDS[card][0] if card in CARDS else "unknown MSI card"


def supported_effects(card):
    """Effect names the card offers, in display order, or None if the card isn't in the table."""
    if card not in CARDS:
        return None
    names = set(CORE) | set(CARDS[card][1])
    return [name for name in EFFECTS if name in names]


def _read(path):
    with open(path) as f:
        return f.read().strip()


def find_gpus():
    """Yield (pci_addr, (device, subsystem), [(bus_number, adapter_name), ...]) for MSI-built NVIDIA GPUs."""
    for dev in sorted(glob.glob("/sys/bus/pci/devices/*")):
        try:
            if not _read(f"{dev}/class").startswith("0x03") or _read(f"{dev}/vendor") != "0x10de":
                continue
            if _read(f"{dev}/subsystem_vendor") != "0x1462":
                continue
            card = (int(_read(f"{dev}/device"), 16), int(_read(f"{dev}/subsystem_device"), 16))
        except OSError:
            continue
        buses = []
        for adapter in glob.glob(f"{dev}/i2c-*"):
            buses.append((int(adapter.rsplit("-", 1)[1]), _read(f"{adapter}/name")))
        yield os.path.basename(dev), card, sorted(buses)


def port_order(buses):
    """The controller is on the GPU's first I2C port ('NVIDIA i2c adapter 1'). Try it first."""
    return sorted(buses, key=lambda b: (" adapter 1 " not in f"{b[1]} ", b[0]))
