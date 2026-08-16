#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Determine si le Seiren a plus de 16 LEDs : 0..15 vert, 16..31 rouge."""
from seiren import SeirenV3Chroma

G = (0, 255, 0)
R = (255, 0, 0)

with SeirenV3Chroma() as s:
    s.set_brightness(0xFF)
    r1 = s.set_custom_frame([G] * 16, start_col=0)
    r2 = s.set_custom_frame([R] * 16, start_col=16)
    print("0..15 vert  : status 0x%02X" % (r1[0] if r1 else 0))
    print("16..31 rouge: status 0x%02X" % (r2[0] if r2 else 0))
    print("--> Anneau tout VERT = <=16 LEDs. VERT + portion ROUGE = >16 LEDs.")
