"""Register protocol of the RGB controller on MSI RTX 40-series cards (I2C address 0x68).

Effects are built as plain op lists so they can be checked without hardware. See docs/protocol.md.
"""

from dataclasses import dataclass

ADDR = 0x68

REG_MODE = 0x22
REG_COLOR1 = 0x27  # 3-byte block, B,G,R
REG_COLOR2 = 0x28
REG_COLOR3 = 0x29
REG_ZONE_OFF = 0x2D  # bitmask of zones forced off
REG_R, REG_G, REG_B = 0x30, 0x31, 0x32
REG_BRIGHTNESS = 0x36
REG_SPEED = 0x38
REG_SAVE = 0x3F
REG_CUSTOM_FLAGS = 0x46  # wave / color-cycle: bit0 custom colors, bit1 reverse
REG_FW_INFO = 0xEC  # read 4: LED type, module type (2, big-endian), firmware version
REG_CHIP_ID = 0xED  # read 2

MODE_PREPARE = 0x1C  # written before nearly every effect

ZONE_SIDE, ZONE_FRONT, ZONE_BACK = 1, 2, 4
ALL_ZONES = ZONE_SIDE | ZONE_FRONT | ZONE_BACK

WRITE_GAP_MS = 20  # pause after each register write
SAVE_DELAY_MS = 1000  # pause before persisting

DEFAULT_COLOR = (255, 0, 0)
DEFAULT_MULTI = ((0, 0, 255), (0, 255, 0), (255, 0, 0))


@dataclass(frozen=True)
class Write:
    reg: int
    data: bytes


@dataclass(frozen=True)
class Sleep:
    ms: int


def w(reg, *values):
    return Write(reg, bytes(values))


def bgr(color):
    r, g, b = color
    return bytes((b, g, r))


def brightness_reg(level):
    """Level 1..5 -> register value in percent (level * 20)."""
    if not 1 <= level <= 5:
        raise ValueError("brightness must be 1..5")
    return level * 20


def speed_reg(level):
    """Level 1..3 (slow..fast) -> effect period register (4, 2, 1)."""
    if not 1 <= level <= 3:
        raise ValueError("speed must be 1..3")
    return 4 - level if level > 1 else 4


def _tune(brightness, speed):
    return [w(REG_BRIGHTNESS, brightness_reg(brightness)), w(REG_SPEED, speed_reg(speed))]


def _rgb(color):
    return [w(REG_R, color[0]), w(REG_G, color[1]), w(REG_B, color[2])]


def _single(mode, color, brightness, speed):
    return [w(REG_MODE, MODE_PREPARE), *_tune(brightness, speed), *_rgb(color), w(REG_MODE, mode)]


def _colorless(mode, brightness, speed):
    return [w(REG_MODE, MODE_PREPARE), *_tune(brightness, speed), w(REG_MODE, mode)]


@dataclass(frozen=True)
class Effect:
    name: str
    colors: int  # number of colors accepted
    rainbow: bool  # supports a rainbow variant (used when no colors are given)
    help: str


EFFECTS = {
    e.name: e
    for e in [
        Effect("off", 0, False, "turn zones off (others keep the last effect)"),
        Effect("static", 1, False, "solid color"),
        Effect("breathing", 2, False, "breathe between two colors"),
        Effect("flashing", 1, False, "flash"),
        Effect("double-flashing", 1, False, "double flash"),
        Effect("marquee", 1, True, "marquee"),
        Effect("stack", 1, True, "stack"),
        Effect("wave", 3, True, "wave (factory default, rainbow)"),
        Effect("meteor", 1, True, "meteor"),
        Effect("lightning", 0, False, "lightning"),
        Effect("rhythm", 1, True, "rhythm"),
        Effect("patrolling", 1, False, "patrolling"),
        Effect("streaming", 0, False, "streaming"),
        Effect("fade-in", 2, False, "fade between two colors"),
        Effect("flowing", 1, True, "flowing"),
        Effect("whirling", 1, True, "whirling"),
        Effect("twisting", 1, True, "twisting"),
        Effect("color-cycle", 3, True, "cycle through three colors"),
        Effect("preset", 1, True, "the card's built-in preset effect"),
    ]
}

_SINGLE_MODES = {"static": 0x13, "flashing": 0x02, "double-flashing": 0x03, "patrolling": 0x05}
_RAINBOW_PAIRS = {  # name: (single-color mode, rainbow mode)
    "marquee": (0x18, 0x19),
    "meteor": (0x16, 0x17),
    "stack": (0x0D, 0x0E),
    "flowing": (0x09, 0x0A),
    "whirling": (0x0F, 0x10),
    "twisting": (0x11, 0x12),
    "rhythm": (0x0B, 0x0C),
}
_COLORLESS_MODES = {"streaming": 0x06, "lightning": 0x15}

# (device, subsystem) of cards whose preset is a fixed static color at 80% brightness
PRESET_IS_STATIC = {(0x2882, 0x5164), (0x2882, 0x5165)}


def build(name, colors=(), rainbow=False, reverse=False, brightness=4, speed=2, zones=ALL_ZONES, card=None,
          save=True):
    """Return the register writes for one effect: re-enable zones -> effect -> optional save."""
    colors = [tuple(c) for c in colors]
    ops = [w(REG_ZONE_OFF, 0)]

    if name == "off":
        ops.append(w(REG_ZONE_OFF, zones))
    elif name in _SINGLE_MODES:
        ops += _single(_SINGLE_MODES[name], (colors or [DEFAULT_COLOR])[0], brightness, speed)
    elif name in _RAINBOW_PAIRS:
        mc, mr = _RAINBOW_PAIRS[name]
        ops += _single(mr if rainbow else mc, (colors or [DEFAULT_COLOR])[0], brightness, speed)
    elif name in _COLORLESS_MODES:
        ops += _colorless(_COLORLESS_MODES[name], brightness, speed)
    elif name == "breathing":
        c1, c2 = colors[:2] if len(colors) >= 2 else DEFAULT_MULTI[:2]
        ops += [w(REG_MODE, MODE_PREPARE), Write(REG_COLOR1, bgr(c1)), Write(REG_COLOR2, bgr(c2)),
                *_tune(brightness, speed), w(REG_MODE, 0x04)]
    elif name == "fade-in":
        c1, c2 = colors[:2] if len(colors) >= 2 else DEFAULT_MULTI[:2]
        ops += [w(REG_MODE, MODE_PREPARE), Write(REG_COLOR2, bgr(c1)), Write(REG_COLOR1, bgr(c2)),
                *_tune(brightness, speed), w(REG_MODE, 0x14)]
    elif name == "wave":
        ops += _wave(colors, rainbow, reverse, brightness, speed)
    elif name == "color-cycle":
        ops.append(w(REG_MODE, MODE_PREPARE))
        if rainbow:
            ops.append(w(REG_CUSTOM_FLAGS, 0))
        else:
            c1, c2, c3 = colors[:3] if len(colors) >= 3 else DEFAULT_MULTI
            ops += [w(REG_CUSTOM_FLAGS, 1), w(REG_MODE, MODE_PREPARE), Write(REG_COLOR1, bgr(c1)),
                    Write(REG_COLOR2, bgr(c2)), Write(REG_COLOR3, bgr(c3))]
        ops += [*_tune(brightness, speed), w(REG_MODE, 0x07)]
    elif name == "preset":
        color = (colors or [DEFAULT_COLOR])[0]
        if card in PRESET_IS_STATIC:
            ops += [w(REG_MODE, MODE_PREPARE), w(REG_BRIGHTNESS, 80), w(REG_SPEED, 1), *_rgb(color), w(REG_MODE, 0x13)]
        elif rainbow:
            ops += [w(REG_MODE, MODE_PREPARE), *_tune(brightness, speed), w(REG_MODE, 0x1E)]
        else:
            ops += [w(REG_MODE, MODE_PREPARE), *_tune(brightness, speed), *_rgb(color), w(REG_MODE, 0x1D)]
    else:
        raise ValueError(f"unknown effect {name!r}")

    if save:
        ops += [Sleep(SAVE_DELAY_MS), w(REG_SAVE, 0)]
    return ops


def _wave(colors, rainbow, reverse, brightness, speed):
    if rainbow:
        ops = [w(REG_CUSTOM_FLAGS, 2 if reverse else 0)]
    else:
        c1, c2, c3 = colors[:3] if len(colors) >= 3 else DEFAULT_MULTI
        if reverse:
            ops = [w(REG_CUSTOM_FLAGS, 3), w(REG_MODE, MODE_PREPARE), Write(REG_COLOR1, bgr(c1)),
                   Write(REG_COLOR2, bgr(c2)), Write(REG_COLOR3, bgr(c3))]
        else:
            ops = [w(REG_CUSTOM_FLAGS, 1), w(REG_MODE, MODE_PREPARE), Write(REG_COLOR3, bgr(c1)),
                   Write(REG_COLOR1, bgr(c2)), Write(REG_COLOR2, bgr(c3))]
    return ops + [*_tune(brightness, speed), w(REG_MODE, 0x08)]


def run(bus, ops, sleep):
    for op in ops:
        if isinstance(op, Sleep):
            sleep(op.ms / 1000)
        else:
            bus.write(ADDR, op.reg, op.data)
            sleep(WRITE_GAP_MS / 1000)


def read_info(bus):
    fw = bus.read(ADDR, REG_FW_INFO, 4)
    chip = bus.read(ADDR, REG_CHIP_ID, 2)
    return {
        "led_type": fw[0],
        "module_type": fw[1] << 8 | fw[2],
        "fw_version": fw[3],
        "chip_id": chip[0] << 8 | chip[1],
    }
