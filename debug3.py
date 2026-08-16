#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test razer_report COMPACT (63 octets, report ID 0x07) sur le Seiren V3 Chroma."""
import time
import hid

VID, PID = 0x1532, 0x056F
TIDS = [0x1F, 0x3F, 0x08, 0x9F, 0xFF, 0x88, 0x80, 0x1A]
STATUS = {0x00: "echo", 0x01: "busy", 0x02: "SUCCESS", 0x03: "FAIL", 0x04: "timeout", 0x05: "unsupported"}


def hx(d):
    return " ".join("%02x" % b for b in d)


def build63(cclass, cid, dsize, args=b"", tid=0x1F):
    """razer_report compact : 63 octets. CRC = XOR [2..60], place en [61]."""
    r = bytearray(63)
    r[0] = 0x00       # status
    r[1] = tid        # transaction_id
    r[5] = dsize      # data_size
    r[6] = cclass     # command_class
    r[7] = cid        # command_id
    for i, b in enumerate(args):
        r[8 + i] = b
    crc = 0
    for i in range(2, 61):
        crc ^= r[i]
    r[61] = crc
    return r


def txn(dev, report, tid, label):
    dev.send_feature_report(bytes([0x07]) + bytes(report))
    time.sleep(0.06)
    resp = dev.get_feature_report(0x07, 64)
    payload = resp[1:] if len(resp) >= 64 else resp
    status = payload[0] if payload else None
    print("  %-18s tid=0x%02X -> status=0x%02X (%s)  data=[%s]" % (
        label, tid, status, STATUS.get(status, "?"), hx(payload[6:16])))
    return payload


devs = [d for d in hid.enumerate(VID, PID) if d.get("usage_page", 0) == 0xFF53]
dev = hid.device()
dev.open_path(devs[0]["path"])
print("Ouvert if#%s 0xFF53\n" % devs[0].get("interface_number"))

print("=== GET FIRMWARE (classe 0x00 / cmd 0x81) ===")
fw_winner = None
for tid in TIDS:
    p = txn(dev, build63(0x00, 0x81, 0x02, b"", tid), tid, "Get Firmware")
    if p and p[0] == 0x02:
        print("    *** SUCCESS tid=0x%02X : firmware v%d.%d ***" % (tid, p[8], p[9]))
        fw_winner = tid
        break

if fw_winner is None:
    print("\nAucun SUCCESS sur Get Firmware. On essaie Get Serial pour confirmer le format...")
    for tid in TIDS:
        p = txn(dev, build63(0x00, 0x82, 0x16, b"", tid), tid, "Get Serial")
        if p and p[0] == 0x02:
            serial = bytes(p[8:8 + 22]).split(b"\x00")[0].decode("ascii", "replace")
            print("    *** SUCCESS tid=0x%02X : serial=%s ***" % (tid, serial))
            fw_winner = tid
            break
else:
    print("\n=== GET SERIAL avec tid gagnant 0x%02X ===" % fw_winner)
    p = txn(dev, build63(0x00, 0x82, 0x16, b"", fw_winner), fw_winner, "Get Serial")
    if p and p[0] == 0x02:
        serial = bytes(p[8:8 + 22]).split(b"\x00")[0].decode("ascii", "replace")
        print("    serial = %s" % serial)

print("\n=== Resume ===")
print("transaction_id gagnant :", ("0x%02X" % fw_winner) if fw_winner is not None else "AUCUN")
dev.close()
