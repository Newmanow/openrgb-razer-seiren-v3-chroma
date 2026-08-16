#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bibliotheque du protocole RGB du Razer Seiren V3 Chroma (USB 1532:056F).

Protocole decouvert par retro-ingenierie (sondage actif) :
  - Interface HID #3, page vendor 0xFF53
  - Feature report ID 0x07, payload de 63 octets
  - Structure "razer_report" compacte (comme openrazer mais 63 octets au lieu de 90)
  - transaction_id = 0x1F
  - Jeu de commandes "Extended Matrix" (command_class 0x0F)
  - CRC = XOR des octets [2..60], place en [61]

Reponse : payload[0] = status (0x02 = SUCCESS).
"""
import time
import hid

VID = 0x1532
PID = 0x056F
VENDOR_USAGE_PAGE = 0xFF53
REPORT_ID = 0x07
TRANSACTION_ID = 0x1F

# LED ids (razercommon.h)
ZERO_LED = 0x00
BACKLIGHT_LED = 0x05
LOGO_LED = 0x04

# Stockage
NOSTORE = 0x00
VARSTORE = 0x01

STATUS = {0x00: "echo", 0x01: "busy", 0x02: "SUCCESS",
          0x03: "FAIL", 0x04: "timeout", 0x05: "unsupported"}


def build_report(command_class, command_id, data_size, args=b"", transaction_id=TRANSACTION_ID):
    """Construit un razer_report compact de 63 octets."""
    r = bytearray(63)
    r[0] = 0x00                 # status
    r[1] = transaction_id       # transaction_id
    r[2] = 0x00                 # remaining_packets hi
    r[3] = 0x00                 # remaining_packets lo
    r[4] = 0x00                 # protocol_type
    r[5] = data_size & 0xFF     # data_size
    r[6] = command_class        # command_class
    r[7] = command_id           # command_id
    for i, b in enumerate(args):
        r[8 + i] = b & 0xFF
    crc = 0
    for i in range(2, 61):
        crc ^= r[i]
    r[61] = crc
    return r


class SeirenError(Exception):
    pass


class SeirenV3Chroma:
    """Pilote bas niveau du Seiren V3 Chroma."""

    def __init__(self):
        self.dev = None

    # ---- connexion ------------------------------------------------------ #
    @staticmethod
    def find_paths():
        return [d for d in hid.enumerate(VID, PID)
                if d.get("usage_page", 0) == VENDOR_USAGE_PAGE]

    def open(self):
        paths = self.find_paths()
        if not paths:
            raise SeirenError("Seiren V3 Chroma introuvable (interface 0xFF53). Micro branche ?")
        self.dev = hid.device()
        self.dev.open_path(paths[0]["path"])
        return self

    def close(self):
        if self.dev:
            self.dev.close()
            self.dev = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        self.close()

    # ---- transaction bas niveau ---------------------------------------- #
    def _txn(self, report, read=True):
        if not self.dev:
            raise SeirenError("Peripherique non ouvert.")
        self.dev.send_feature_report(bytes([REPORT_ID]) + bytes(report))
        if not read:
            return None
        time.sleep(0.04)
        resp = self.dev.get_feature_report(REPORT_ID, 64)
        return resp[1:] if len(resp) >= 64 else resp

    # ---- commandes ------------------------------------------------------ #
    def get_firmware(self):
        p = self._txn(build_report(0x00, 0x81, 0x02))
        if p and p[0] == 0x02:
            return (p[8], p[9])
        return None

    def get_serial(self):
        p = self._txn(build_report(0x00, 0x82, 0x16))
        if p and p[0] == 0x02:
            return bytes(p[8:8 + 22]).split(b"\x00")[0].decode("ascii", "replace")
        return None

    def set_brightness(self, level, led=ZERO_LED, varstore=VARSTORE):
        return self._txn(build_report(0x0F, 0x04, 0x03, bytes([varstore, led, level])))

    def set_static(self, r, g, b, led=ZERO_LED, varstore=VARSTORE):
        args = bytes([varstore, led, 0x01, 0x00, 0x00, 0x01, r, g, b])
        return self._txn(build_report(0x0F, 0x02, 0x09, args))

    def set_spectrum(self, led=ZERO_LED, varstore=VARSTORE):
        return self._txn(build_report(0x0F, 0x02, 0x06, bytes([varstore, led, 0x03, 0, 0, 0])))

    def set_wave(self, direction=0x00, speed=0x28, led=ZERO_LED, varstore=VARSTORE):
        # effect 0x04 = wave ; direction 0x00/0x01
        return self._txn(build_report(0x0F, 0x02, 0x06,
                                      bytes([varstore, led, 0x04, direction & 0x01, speed, 0x00])))

    def set_off(self, led=ZERO_LED, varstore=VARSTORE):
        return self._txn(build_report(0x0F, 0x02, 0x06, bytes([varstore, led, 0x00, 0, 0, 0])))

    # Un paquet de 63 octets : args = [8..60] (53 octets). En-tete custom frame = 5
    # octets, donc 48 octets de RGB max => 16 LEDs maximum par paquet.
    MAX_LEDS_PER_PACKET = 16

    def set_custom_frame(self, rgb_list, row=0, start_col=0):
        """rgb_list : liste de (r,g,b). Affiche via la custom frame extended (0x0F/0x03).
        Limite a 16 LEDs par paquet (taille du report compact)."""
        rgb_list = rgb_list[:self.MAX_LEDS_PER_PACKET]
        data = bytearray()
        for (r, g, b) in rgb_list:
            data += bytes([r & 0xFF, g & 0xFF, b & 0xFF])
        stop_col = start_col + len(rgb_list) - 1
        args = bytes([0x00, 0x00, row, start_col, stop_col]) + data
        data_size = 5 + 3 * len(rgb_list)
        return self._txn(build_report(0x0F, 0x03, data_size, args))


if __name__ == "__main__":
    with SeirenV3Chroma() as s:
        print("Firmware :", s.get_firmware())
        print("Serial   :", s.get_serial())
