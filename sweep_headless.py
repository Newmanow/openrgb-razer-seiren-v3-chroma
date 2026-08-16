#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sweep headless : trouve le transaction_id du Seiren V3 Chroma via Get Firmware.
Commande de lecture seule (inoffensive)."""
import time
import hid

RAZER_VID = 0x1532
PID = 0x056F
TRANSACTION_IDS = [0x1F, 0x3F, 0x08, 0x9F, 0xFF, 0x88, 0x80, 0x1A, 0x00]
STATUS = {0x00: "echo", 0x01: "busy", 0x02: "SUCCESS", 0x03: "FAIL", 0x04: "timeout", 0x05: "unsupported"}


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


def try_path(d):
    path = d["path"]
    print("\n=== Interface if#%s usage_page=0x%04X usage=0x%04X ===" % (
        d.get("interface_number"), d.get("usage_page", 0), d.get("usage", 0)))
    try:
        dev = hid.device()
        dev.open_path(path)
    except Exception as e:
        print("  [open echoue] %s" % e)
        return []
    winners = []
    for tid in TRANSACTION_IDS:
        rep = build_report(0x00, 0x81, 0x02, b"", tid)  # Get Firmware
        try:
            dev.send_feature_report(bytes([0x00]) + bytes(rep))
        except Exception as e:
            print("  tid=0x%02X  envoi echoue: %s" % (tid, e))
            continue
        time.sleep(0.06)
        try:
            resp = dev.get_feature_report(0x00, 91)
        except Exception as e:
            print("  tid=0x%02X  lecture echouee: %s" % (tid, e))
            continue
        if not resp or len(resp) < 10:
            print("  tid=0x%02X  reponse vide" % tid)
            continue
        payload = resp[1:] if len(resp) >= 91 else resp
        status = payload[0]
        tag = STATUS.get(status, "?")
        extra = ""
        if status == 0x02:
            extra = "  fw v%d.%d" % (payload[8], payload[9])
            winners.append((tid, payload[8], payload[9]))
        print("  tid=0x%02X  -> status=0x%02X (%s)%s" % (tid, status, tag, extra))
        time.sleep(0.02)
    dev.close()
    return winners


def main():
    devs = list(hid.enumerate(RAZER_VID, PID))
    if not devs:
        print("Aucune interface HID pour 1532:056F (micro branche ?)")
        return
    # On teste d'abord la page vendor 0xFF53, puis les autres
    devs.sort(key=lambda d: 0 if d.get("usage_page", 0) == 0xFF53 else 1)
    all_winners = []
    for d in devs:
        w = try_path(d)
        if w:
            all_winners.append((d, w))
    print("\n========================================")
    if all_winners:
        for d, w in all_winners:
            for (tid, maj, minr) in w:
                print("GAGNANT: if#%s usage_page=0x%04X  transaction_id=0x%02X  firmware=v%d.%d" % (
                    d.get("interface_number"), d.get("usage_page", 0), tid, maj, minr))
    else:
        print("Aucun transaction_id n'a repondu SUCCESS. (a creuser via la GUI / autres commandes)")


if __name__ == "__main__":
    main()
