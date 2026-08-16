#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiche 16 couleurs distinctes pour compter les LEDs du Seiren."""
import colorsys
from seiren import SeirenV3Chroma

# 16 teintes bien reparties
colors = []
for i in range(16):
    h = i / 16.0
    r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
    colors.append((int(r * 255), int(g * 255), int(b * 255)))

with SeirenV3Chroma() as s:
    s.set_brightness(0xFF)
    r = s.set_custom_frame(colors, start_col=0)
    print("16 couleurs distinctes envoyees : status 0x%02X" % (r[0] if r else 0))
    for i, c in enumerate(colors):
        print("  LED %2d : RGB%s" % (i, c))
    print("--> Compte les LEDs distinctes autour de l'anneau.")
