#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test du canal report ID 0x07 (63 octets) sur l'interface vendor 0xFF53."""
import time
import hid

VID, PID = 0x1532, 0x056F


def hx(data):
    return " ".join("%02x" % b for b in data)


devs = [d for d in hid.enumerate(VID, PID) if d.get("usage_page", 0) == 0xFF53]
if not devs:
    print("Interface 0xFF53 introuvable.")
    raise SystemExit

dev = hid.device()
dev.open_path(devs[0]["path"])
print("Ouvert : if#%s usage_page=0xFF53" % devs[0].get("interface_number"))

# 1) LECTURE SEULE : que contient le feature report 0x07 au repos ?
print("\n--- GET_FEATURE report 0x07 (avant tout envoi) ---")
try:
    resp = dev.get_feature_report(0x07, 64)
    print("  %d octets: %s" % (len(resp), hx(resp)))
except Exception as e:
    print("  EXC:", e)

# 2) GET_INPUT reports
for rid, length in ((0x07, 64), (0x05, 16)):
    print("\n--- GET_INPUT report 0x%02X ---" % rid)
    try:
        resp = dev.get_input_report(rid, length)
        print("  %d octets: %s" % (len(resp), hx(resp)))
    except Exception as e:
        print("  EXC:", e)

# 3) SEND_FEATURE report 0x07 : verifier que le canal accepte l'ecriture
#    Payload = 63 octets a zero (test inoffensif : on verifie juste le code retour)
print("\n--- SEND_FEATURE report 0x07, 64 octets (payload zero) ---")
buf = bytes([0x07]) + bytes(63)
try:
    ret = dev.send_feature_report(buf)
    print("  ret =", ret, "(>0 = accepte)")
except Exception as e:
    print("  EXC:", e)

# 4) Relire apres envoi
print("\n--- GET_FEATURE report 0x07 (apres envoi zero) ---")
time.sleep(0.05)
try:
    resp = dev.get_feature_report(0x07, 64)
    print("  %d octets: %s" % (len(resp), hx(resp)))
except Exception as e:
    print("  EXC:", e)

dev.close()
