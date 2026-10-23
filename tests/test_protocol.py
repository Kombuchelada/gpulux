"""Register sequences per effect, as (register, bytes) pairs at brightness level 4 / speed level 2.
These mirror the tables in docs/protocol.md."""

import unittest

from gpulux import devices, protocol
from gpulux.cli import build_ops, make_parser

RESET = [(0x2D, [0])]
SAVE = ["sleep1000", (0x3F, [0])]
TUNE = [(0x36, [80]), (0x38, [2])]
RGB = [(0x30, [0x12]), (0x31, [0x34]), (0x32, [0x56])]
C1, C2, C3 = (1, 2, 3), (4, 5, 6), (7, 8, 9)
TESTED_CARD = (0x2782, 0x5133)


def flat(ops):
    return ["sleep1000" if isinstance(o, protocol.Sleep) else (o.reg, list(o.data)) for o in ops]


def single(mode):
    return RESET + [(0x22, [28])] + TUNE + RGB + [(0x22, [mode])] + SAVE


class Sequences(unittest.TestCase):
    def check(self, expected, name, colors=(), **kw):
        self.assertEqual(flat(protocol.build(name, colors, brightness=4, speed=2, **kw)), expected)

    def test_single_color_effects(self):
        for name, mode in [("static", 19), ("flashing", 2), ("double-flashing", 3), ("patrolling", 5)]:
            self.check(single(mode), name, [(0x12, 0x34, 0x56)])

    def test_color_or_rainbow_pairs(self):
        for name, color_mode, rainbow_mode in [("marquee", 24, 25), ("meteor", 22, 23), ("stack", 13, 14),
                                               ("flowing", 9, 10), ("whirling", 15, 16), ("twisting", 17, 18),
                                               ("rhythm", 11, 12)]:
            self.check(single(color_mode), name, [(0x12, 0x34, 0x56)])
            self.check(single(rainbow_mode), name, [(0x12, 0x34, 0x56)], rainbow=True)

    def test_colorless(self):
        self.check(RESET + [(0x22, [28])] + TUNE + [(0x22, [6])] + SAVE, "streaming")
        self.check(RESET + [(0x22, [28])] + TUNE + [(0x22, [21])] + SAVE, "lightning")

    def test_breathing_bgr_blocks(self):
        self.check(RESET + [(0x22, [28]), (0x27, [3, 2, 1]), (0x28, [6, 5, 4])] + TUNE + [(0x22, [4])] + SAVE,
                   "breathing", [C1, C2])

    def test_fade_in_uses_slot_2_first(self):
        self.check(RESET + [(0x22, [28]), (0x28, [3, 2, 1]), (0x27, [6, 5, 4])] + TUNE + [(0x22, [20])] + SAVE,
                   "fade-in", [C1, C2])

    def test_wave(self):
        self.check(RESET + [(0x46, [0])] + TUNE + [(0x22, [8])] + SAVE, "wave", rainbow=True)
        self.check(RESET + [(0x46, [2])] + TUNE + [(0x22, [8])] + SAVE, "wave", rainbow=True, reverse=True)
        self.check(RESET + [(0x46, [1]), (0x22, [28]), (0x29, [3, 2, 1]), (0x27, [6, 5, 4]), (0x28, [9, 8, 7])]
                   + TUNE + [(0x22, [8])] + SAVE, "wave", [C1, C2, C3])
        self.check(RESET + [(0x46, [3]), (0x22, [28]), (0x27, [3, 2, 1]), (0x28, [6, 5, 4]), (0x29, [9, 8, 7])]
                   + TUNE + [(0x22, [8])] + SAVE, "wave", [C1, C2, C3], reverse=True)

    def test_color_cycle(self):
        self.check(RESET + [(0x22, [28]), (0x46, [0])] + TUNE + [(0x22, [7])] + SAVE, "color-cycle", rainbow=True)
        self.check(RESET + [(0x22, [28]), (0x46, [1]), (0x22, [28]), (0x27, [3, 2, 1]), (0x28, [6, 5, 4]),
                            (0x29, [9, 8, 7])] + TUNE + [(0x22, [7])] + SAVE, "color-cycle", [C1, C2, C3])

    def test_preset(self):
        self.check(RESET + [(0x22, [28])] + TUNE + [(0x22, [30])] + SAVE, "preset", rainbow=True)
        self.check(single(29), "preset", [(0x12, 0x34, 0x56)])
        self.check(RESET + [(0x22, [28]), (0x36, [80]), (0x38, [1])] + RGB + [(0x22, [19])] + SAVE,
                   "preset", [(0x12, 0x34, 0x56)], card=(0x2882, 0x5164))

    def test_off_zone_mask(self):
        self.check(RESET + [(0x2D, [7])] + SAVE, "off")
        self.check(RESET + [(0x2D, [protocol.ZONE_SIDE | protocol.ZONE_BACK])] + SAVE, "off",
                   zones=protocol.ZONE_SIDE | protocol.ZONE_BACK)

    def test_no_save(self):
        self.assertEqual(flat(protocol.build("lightning", save=False))[-1], (0x22, [21]))

    def test_speed_and_brightness_mapping(self):
        self.assertEqual([protocol.speed_reg(s) for s in (1, 2, 3)], [4, 2, 1])
        self.assertEqual([protocol.brightness_reg(b) for b in range(1, 6)], [20, 40, 60, 80, 100])


class Cards(unittest.TestCase):
    def test_tested_card_effects(self):
        self.assertEqual(sorted(devices.supported_effects(TESTED_CARD)), sorted([
            "off", "wave", "streaming", "color-cycle", "flowing", "stack", "whirling", "twisting", "lightning",
            "marquee", "fade-in", "patrolling", "breathing", "flashing", "double-flashing", "static", "preset"]))

    def test_every_listed_effect_is_implemented(self):
        for card, (_name, extra) in devices.CARDS.items():
            self.assertLessEqual(set(extra), set(protocol.EFFECTS), card)

    def test_port_1_first(self):
        buses = [(3, "NVIDIA i2c adapter 2 at 1:00.0"), (2, "NVIDIA i2c adapter 1 at 1:00.0")]
        self.assertEqual(devices.port_order(buses)[0][0], 2)


class Cli(unittest.TestCase):
    def ops(self, *argv):
        return flat(build_ops(make_parser().parse_args(list(argv)), TESTED_CARD))

    def test_rainbow_when_no_color(self):
        self.assertIn((0x22, [25]), self.ops("marquee"))
        self.assertIn((0x22, [24]), self.ops("marquee", "red"))

    def test_static_needs_color(self):
        with self.assertRaises(SystemExit):
            self.ops("static")

    def test_unlisted_effect_rejected(self):
        with self.assertRaises(SystemExit):
            self.ops("meteor", "red")


if __name__ == "__main__":
    unittest.main()
