#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug bas niveau : comprendre comment parler au Seiren V3 Chroma."""
import time
import hid

PID = 0x056F
VID = 0x1532


def build_report(cclass, cid, dsize, args=b"", tid=0x1F):
    r = bytearray(90)
    r[1] = tid
    r[5] = dsize
    r[6] = cclass
    r[7] = cid
    for i, b in enumerate(args):
        r[8 + i] = b
    crc = 0
    for i in range(2, 88):
        crc ^= r[i]
    r[88] = crc
    return r


print("hidapi version attr:", getattr(hid, "__version__", "?"))
dev = hid.device()
print("Methodes dispo sur hid.device():")
print("  ", [m for m in dir(dev) if not m.startswith("_")])

devs = list(hid.enumerate(VID, PID))
devs.sort(key=lambda d: 0 if d.get("usage_page", 0) == 0xFF53 else 1)

for d in devs:
    print("\n############################################################")
    print("Interface if#%s usage_page=0x%04X usage=0x%04X" % (
        d.get("interface_number"), d.get("usage_page", 0), d.get("usage", 0)))
    try:
        dev = hid.device()
        dev.open_path(d["path"])
    except Exception as e:
        print("  open echoue:", e)
        continue

    # 1) Report descriptor (si dispo dans cette version de hidapi)
    if hasattr(dev, "get_report_descriptor"):
        try:
            desc = dev.get_report_descriptor()
            print("  report_descriptor (%d octets): %s" % (len(desc), " ".join("%02x" % b for b in desc)))
        except Exception as e:
            print("  get_report_descriptor echoue:", e)
    else:
        print("  (pas de methode get_report_descriptor dans cette version)")

    # 2) send_feature_report : tester plusieurs longueurs et lire le code retour
    fw = build_report(0x00, 0x81, 0x02, b"", 0x1F)
    for total in (91, 90, 65, 64, 17, 33):
        buf = bytes([0x00]) + bytes(fw)
        buf = buf[:total] + bytes(max(0, total - len(buf)))
        try:
            ret = dev.send_feature_report(buf)
            print("  send_feature_report len=%d -> ret=%s" % (total, ret))
        except Exception as e:
            print("  send_feature_report len=%d -> EXC %s" % (total, e))

    # 3) get_feature_report : tester plusieurs longueurs
    time.sleep(0.05)
    for total in (91, 90, 65, 64, 17, 33):
        try:
            resp = dev.get_feature_report(0x00, total)
            print("  get_feature_report len=%d -> %d octets: %s" % (
                total, len(resp), " ".join("%02x" % b for b in resp[:16])))
        except Exception as e:
            print("  get_feature_report len=%d -> EXC %s" % (total, e))

    dev.close()
