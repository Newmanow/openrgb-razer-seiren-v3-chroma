#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan des commandes d'eclairage acceptees par le Seiren V3 Chroma.
Format : razer_report compact 63 octets, report ID 0x07, transaction_id 0x1F."""
import time
import hid

VID, PID, TID = 0x1532, 0x056F, 0x1F
STATUS = {0x00: "echo", 0x01: "busy", 0x02: "SUCCESS", 0x03: "FAIL", 0x04: "timeout", 0x05: "unsupported"}


def hx(d):
    return " ".join("%02x" % b for b in d)


def build63(cclass, cid, dsize, args=b"", tid=TID):
    r = bytearray(63)
    r[1] = tid
    r[5] = dsize
    r[6] = cclass
    r[7] = cid
    for i, b in enumerate(args):
        r[8 + i] = b
    crc = 0
    for i in range(2, 61):
        crc ^= r[i]
    r[61] = crc
    return r


def txn(dev, report, label):
    dev.send_feature_report(bytes([0x07]) + bytes(report))
    time.sleep(0.05)
    resp = dev.get_feature_report(0x07, 64)
    p = resp[1:] if len(resp) >= 64 else resp
    st = p[0] if p else None
    flag = " <== ACCEPTE" if st == 0x02 else ""
    print("  %-40s -> 0x%02X (%s)%s" % (label, st, STATUS.get(st, "?"), flag))
    return p


devs = [d for d in hid.enumerate(VID, PID) if d.get("usage_page", 0) == 0xFF53]
dev = hid.device()
dev.open_path(devs[0]["path"])
print("Ouvert if#%s 0xFF53, tid=0x%02X\n" % (devs[0].get("interface_number"), TID))

R = (0xFF, 0x00, 0x00)

print("=== Commandes STATIC (rouge) ===")
# Extended static (0x0F/0x02) : [varstore, led, 0x01, 0,0, 0x01, R,G,B]
for vs in (0x01, 0x00):
    for led in (0x00, 0x05, 0x04):
        txn(dev, build63(0x0F, 0x02, 0x09, bytes([vs, led, 0x01, 0, 0, 0x01, *R])),
            "Ext static  vs=0x%02X led=0x%02X" % (vs, led))
# Standard static (0x03/0x0A) : [0x06, R,G,B]
txn(dev, build63(0x03, 0x0A, 0x04, bytes([0x06, *R])), "Std static")
# Mouse-ext static (0x03/0x0D) : [varstore, led, 0x06, R,G,B]
for led in (0x00, 0x05):
    txn(dev, build63(0x03, 0x0D, 0x06, bytes([0x01, led, 0x06, *R])),
        "MouseExt static led=0x%02X" % led)

print("\n=== Commandes BRIGHTNESS (max) ===")
for led in (0x00, 0x05):
    txn(dev, build63(0x0F, 0x04, 0x03, bytes([0x01, led, 0xFF])), "Ext brightness led=0x%02X" % led)
    txn(dev, build63(0x03, 0x03, 0x03, bytes([0x01, led, 0xFF])), "Std brightness led=0x%02X" % led)

print("\n=== Effets divers ===")
txn(dev, build63(0x0F, 0x02, 0x06, bytes([0x01, 0x00, 0x04, 0x00, 0x28, 0x00])), "Ext WAVE led=0x00")
txn(dev, build63(0x0F, 0x02, 0x06, bytes([0x01, 0x00, 0x03, 0, 0, 0])), "Ext SPECTRUM led=0x00")
txn(dev, build63(0x03, 0x00, 0x03, bytes([0x01, 0x00, 0x01])), "Set LED state ON led=0x00")

print("\n=== Custom frame (allume 10 LEDs rouge) ===")
# Extended custom frame (0x0F/0x03) : [00,00,row,start,stop, RGB...]
n = 10
rgb = bytes([0xFF, 0x00, 0x00]) * n
txn(dev, build63(0x0F, 0x03, 0x47, bytes([0x00, 0x00, 0x00, 0x00, n - 1]) + rgb), "Ext custom frame 10 LEDs")

print("\n(Regarde le micro : a-t-il change de couleur a un moment ?)")
dev.close()
