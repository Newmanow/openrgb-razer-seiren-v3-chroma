#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Razer Seiren V3 Chroma - Outil de sondage du protocole RGB
===========================================================

Objectif : decouvrir EXPERIMENTALEMENT les parametres necessaires pour ajouter
le micro Razer Seiren V3 Chroma (USB 1532:056F) au driver Razer d'OpenRGB :

  1. le bon `transaction_id`  (via "Get Firmware Version")
  2. la bonne interface HID
  3. le bon variant de commande (Standard / Extended / Mouse-Extended)
  4. le nombre de LEDs (via la "Custom Frame")

Le protocole "razer report" (90 octets) est repris a l'identique d'openrazer.
Aucune capture USB (pcap) n'est necessaire : on envoie nos propres paquets et
on observe le micro + les reponses du peripherique.

Dependances : Python 3 + `pip install hidapi`  (module importe sous le nom `hid`)
"""

import sys
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, colorchooser, messagebox

try:
    import hid
except ImportError:
    print("Module 'hid' manquant. Installe-le avec :  python -m pip install hidapi")
    sys.exit(1)

# --------------------------------------------------------------------------- #
#  Constantes du peripherique et du protocole (extraites d'openrazer)
# --------------------------------------------------------------------------- #
RAZER_VID = 0x1532
SEIREN_V3_CHROMA_PID = 0x056F

# Codes de statut renvoyes dans l'octet [0] de la reponse
STATUS = {
    0x00: "new command (echo)",
    0x01: "busy / wait",
    0x02: "SUCCESS",
    0x03: "FAILURE",
    0x04: "timeout",
    0x05: "not supported",
}

# transaction_id candidats a tester (du plus probable au moins probable)
TRANSACTION_IDS = [0x1F, 0x3F, 0x08, 0x9F, 0xFF, 0x88, 0x80, 0x1A]

# Stockage : NOSTORE / VARSTORE
VARSTORE_OPTIONS = {"VARSTORE (0x01)": 0x01, "NOSTORE (0x00)": 0x00}

# Identifiants de LED courants (razercommon.h)
LED_OPTIONS = {
    "ZERO_LED (0x00)": 0x00,
    "BACKLIGHT_LED (0x05)": 0x05,
    "LOGO_LED (0x04)": 0x04,
    "SCROLL_WHEEL (0x01)": 0x01,
    "ARGB_CH_1 (0x1A)": 0x1A,
    "ARGB_CH_2 (0x1B)": 0x1B,
}

# Variants de jeu de commandes "static / off / custom frame"
PROTO_STANDARD = "Standard (0x03/0x0A)"
PROTO_EXTENDED = "Extended (0x0F/0x02)"
PROTO_MOUSE_EXT = "Mouse-Ext (0x03/0x0D)"
PROTO_OPTIONS = [PROTO_EXTENDED, PROTO_STANDARD, PROTO_MOUSE_EXT]


# --------------------------------------------------------------------------- #
#  Construction d'un "razer report" (90 octets) + CRC
# --------------------------------------------------------------------------- #
def build_report(command_class, command_id, data_size, args=b"", transaction_id=0x1F):
    """Construit le paquet de 90 octets identique a struct razer_report."""
    report = bytearray(90)
    report[0] = 0x00              # status (0 = nouvelle commande)
    report[1] = transaction_id    # transaction_id
    report[2] = 0x00              # remaining_packets (hi)
    report[3] = 0x00              # remaining_packets (lo)
    report[4] = 0x00              # protocol_type
    report[5] = data_size & 0xFF  # data_size
    report[6] = command_class     # command_class
    report[7] = command_id        # command_id
    for i, b in enumerate(args):
        report[8 + i] = b & 0xFF
    crc = 0
    for i in range(2, 88):        # CRC = XOR des octets [2..87]
        crc ^= report[i]
    report[88] = crc
    report[89] = 0x00             # reserved
    return report


def hexdump(data):
    return " ".join("%02x" % b for b in data)


# --------------------------------------------------------------------------- #
#  Builders de commandes (valeurs exactes openrazer)
# --------------------------------------------------------------------------- #
def cmd_get_firmware(tid):
    return build_report(0x00, 0x81, 0x02, b"", tid)


def cmd_get_serial(tid):
    return build_report(0x00, 0x82, 0x16, b"", tid)


def cmd_static(proto, varstore, led, rgb, tid):
    r, g, b = rgb
    if proto == PROTO_STANDARD:
        # classe 0x03 / cmd 0x0A : args = [STATIC=0x06, R, G, B]
        return build_report(0x03, 0x0A, 0x04, bytes([0x06, r, g, b]), tid)
    if proto == PROTO_EXTENDED:
        # classe 0x0F / cmd 0x02 : args = [varstore, led, 0x01, 0,0, 0x01, R,G,B]
        return build_report(0x0F, 0x02, 0x09,
                            bytes([varstore, led, 0x01, 0x00, 0x00, 0x01, r, g, b]), tid)
    # Mouse-Ext : classe 0x03 / cmd 0x0D : args = [varstore, led, 0x06, R,G,B]
    return build_report(0x03, 0x0D, 0x06, bytes([varstore, led, 0x06, r, g, b]), tid)


def cmd_off(proto, varstore, led, tid):
    if proto == PROTO_STANDARD:
        return build_report(0x03, 0x0A, 0x01, bytes([0x00]), tid)
    if proto == PROTO_EXTENDED:
        return build_report(0x0F, 0x02, 0x06, bytes([varstore, led, 0x00, 0, 0, 0]), tid)
    return build_report(0x03, 0x0D, 0x03, bytes([varstore, led, 0x00]), tid)


def cmd_brightness(proto, varstore, led, level, tid):
    if proto == PROTO_EXTENDED:
        # extended brightness : classe 0x0F / cmd 0x04
        return build_report(0x0F, 0x04, 0x03, bytes([varstore, led, level]), tid)
    # standard brightness : classe 0x03 / cmd 0x03
    return build_report(0x03, 0x03, 0x03, bytes([varstore, led, level]), tid)


def cmd_led_state(varstore, led, state, tid):
    # classe 0x03 / cmd 0x00 : args = [varstore, led, state]
    return build_report(0x03, 0x00, 0x03, bytes([varstore, led, state]), tid)


def cmd_custom_frame(proto, row, start_col, stop_col, rgb_list, tid):
    """rgb_list = liste de (r,g,b) pour les colonnes start..stop."""
    data = bytearray()
    for (r, g, b) in rgb_list:
        data += bytes([r, g, b])
    if proto == PROTO_EXTENDED:
        # classe 0x0F / cmd 0x03 : args[2]=row, [3]=start, [4]=stop, RGB a partir de [5]
        args = bytearray([0x00, 0x00, row, start_col, stop_col]) + data
        return build_report(0x0F, 0x03, 0x47, bytes(args), tid)
    # Standard : classe 0x03 / cmd 0x0B : args=[0xFF, row, start, stop, RGB...]
    args = bytearray([0xFF, row, start_col, stop_col]) + data
    return build_report(0x03, 0x0B, 0x46, bytes(args), tid)


def cmd_effect_custom_standard(tid):
    # Active l'affichage de la custom frame sur les devices "standard"
    return build_report(0x03, 0x0A, 0x02, bytes([0x05, 0x00]), tid)


# --------------------------------------------------------------------------- #
#  Application GUI
# --------------------------------------------------------------------------- #
class ProbeApp:
    def __init__(self, root):
        self.root = root
        self.dev = None
        self.dev_path = None
        self.interfaces = []
        self.color = (0, 255, 0)  # vert par defaut

        root.title("Razer Seiren V3 Chroma - Sondeur de protocole RGB")
        root.geometry("960x720")

        self._build_device_frame()
        self._build_params_frame()
        self._build_actions_frame()
        self._build_log_frame()

        self.refresh_devices()

    # ---- Section peripherique -------------------------------------------- #
    def _build_device_frame(self):
        f = ttk.LabelFrame(self.root, text="1. Peripherique")
        f.pack(fill="x", padx=8, pady=4)

        self.dev_combo = ttk.Combobox(f, width=90, state="readonly")
        self.dev_combo.grid(row=0, column=0, columnspan=3, padx=4, pady=4, sticky="w")

        ttk.Button(f, text="Rafraichir", command=self.refresh_devices).grid(row=1, column=0, padx=4, pady=4)
        ttk.Button(f, text="Connecter", command=self.connect).grid(row=1, column=1, padx=4, pady=4)
        self.status_lbl = ttk.Label(f, text="Non connecte", foreground="red")
        self.status_lbl.grid(row=1, column=2, padx=8, sticky="w")

    # ---- Section parametres ---------------------------------------------- #
    def _build_params_frame(self):
        f = ttk.LabelFrame(self.root, text="2. Parametres")
        f.pack(fill="x", padx=8, pady=4)

        ttk.Label(f, text="transaction_id :").grid(row=0, column=0, padx=4, pady=4, sticky="e")
        self.tid_combo = ttk.Combobox(f, width=10, state="readonly",
                                      values=["0x%02X" % t for t in TRANSACTION_IDS])
        self.tid_combo.current(0)
        self.tid_combo.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(f, text="Protocole :").grid(row=0, column=2, padx=4, pady=4, sticky="e")
        self.proto_combo = ttk.Combobox(f, width=22, state="readonly", values=PROTO_OPTIONS)
        self.proto_combo.current(0)
        self.proto_combo.grid(row=0, column=3, padx=4, pady=4, sticky="w")

        ttk.Label(f, text="Stockage :").grid(row=1, column=0, padx=4, pady=4, sticky="e")
        self.var_combo = ttk.Combobox(f, width=18, state="readonly", values=list(VARSTORE_OPTIONS))
        self.var_combo.current(0)
        self.var_combo.grid(row=1, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(f, text="LED id :").grid(row=1, column=2, padx=4, pady=4, sticky="e")
        self.led_combo = ttk.Combobox(f, width=22, state="readonly", values=list(LED_OPTIONS))
        self.led_combo.current(0)
        self.led_combo.grid(row=1, column=3, padx=4, pady=4, sticky="w")

        ttk.Label(f, text="Couleur :").grid(row=2, column=0, padx=4, pady=4, sticky="e")
        self.color_btn = tk.Button(f, text="Choisir...", width=12, bg="#00ff00",
                                   command=self.pick_color)
        self.color_btn.grid(row=2, column=1, padx=4, pady=4, sticky="w")

    # ---- Section actions ------------------------------------------------- #
    def _build_actions_frame(self):
        f = ttk.LabelFrame(self.root, text="3. Actions")
        f.pack(fill="x", padx=8, pady=4)

        # Ligne diagnostic
        ttk.Label(f, text="Diagnostic :").grid(row=0, column=0, padx=4, pady=2, sticky="e")
        ttk.Button(f, text="SWEEP auto (trouver transaction_id)",
                   command=self.sweep_transaction_ids).grid(row=0, column=1, columnspan=2, padx=4, pady=2, sticky="w")
        ttk.Button(f, text="Get Firmware", command=self.get_firmware).grid(row=0, column=3, padx=4, pady=2, sticky="w")
        ttk.Button(f, text="Get Serial", command=self.get_serial).grid(row=0, column=4, padx=4, pady=2, sticky="w")

        # Ligne lumiere
        ttk.Label(f, text="Lumiere :").grid(row=1, column=0, padx=4, pady=2, sticky="e")
        ttk.Button(f, text="STATIC (couleur)", command=self.send_static).grid(row=1, column=1, padx=4, pady=2, sticky="w")
        ttk.Button(f, text="OFF", command=self.send_off).grid(row=1, column=2, padx=4, pady=2, sticky="w")
        ttk.Button(f, text="Brightness MAX", command=lambda: self.send_brightness(0xFF)).grid(row=1, column=3, padx=4, pady=2, sticky="w")
        ttk.Button(f, text="LED State ON", command=self.send_led_on).grid(row=1, column=4, padx=4, pady=2, sticky="w")

        # Ligne comptage de LEDs
        ttk.Label(f, text="Compter LEDs :").grid(row=2, column=0, padx=4, pady=2, sticky="e")
        ttk.Label(f, text="Nb LEDs :").grid(row=2, column=1, padx=4, pady=2, sticky="e")
        self.nleds_entry = ttk.Entry(f, width=6)
        self.nleds_entry.insert(0, "8")
        self.nleds_entry.grid(row=2, column=2, padx=4, pady=2, sticky="w")
        ttk.Button(f, text="Allumer N LEDs (custom frame)",
                   command=self.send_custom_frame).grid(row=2, column=3, columnspan=2, padx=4, pady=2, sticky="w")

    # ---- Section log ----------------------------------------------------- #
    def _build_log_frame(self):
        f = ttk.LabelFrame(self.root, text="Journal")
        f.pack(fill="both", expand=True, padx=8, pady=4)
        self.log = scrolledtext.ScrolledText(f, height=18, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

    # --------------------------------------------------------------------- #
    #  Helpers
    # --------------------------------------------------------------------- #
    def log_msg(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.root.update_idletasks()

    def pick_color(self):
        rgb, _ = colorchooser.askcolor(initialcolor="#%02x%02x%02x" % self.color)
        if rgb:
            self.color = tuple(int(c) for c in rgb)
            self.color_btn.config(bg="#%02x%02x%02x" % self.color)

    def get_tid(self):
        return int(self.tid_combo.get(), 16)

    def get_proto(self):
        return self.proto_combo.get()

    def get_varstore(self):
        return VARSTORE_OPTIONS[self.var_combo.get()]

    def get_led(self):
        return LED_OPTIONS[self.led_combo.get()]

    # --------------------------------------------------------------------- #
    #  Detection / connexion
    # --------------------------------------------------------------------- #
    def refresh_devices(self):
        self.interfaces = []
        items = []
        try:
            for d in hid.enumerate(RAZER_VID, SEIREN_V3_CHROMA_PID):
                self.interfaces.append(d)
                items.append(
                    "if#%s  usage_page=0x%04X  usage=0x%04X  '%s'" % (
                        d.get("interface_number"),
                        d.get("usage_page", 0),
                        d.get("usage", 0),
                        d.get("product_string", "?"),
                    )
                )
        except Exception as e:
            self.log_msg("[ERREUR] enumerate : %s" % e)

        if not items:
            # Aucun Seiren : on liste tous les peripheriques Razer pour aider au diagnostic
            self.log_msg("[INFO] Aucune interface HID trouvee pour 1532:056F.")
            self.log_msg("[INFO] Peripheriques Razer (VID 0x1532) detectes :")
            found_any = False
            for d in hid.enumerate(RAZER_VID, 0):
                found_any = True
                self.log_msg("       PID=0x%04X  if#%s  '%s'" % (
                    d.get("product_id"), d.get("interface_number"), d.get("product_string", "?")))
            if not found_any:
                self.log_msg("       (aucun peripherique Razer du tout - micro branche ?)")
            self.dev_combo["values"] = []
            return

        self.dev_combo["values"] = items
        self.dev_combo.current(0)
        self.log_msg("[OK] %d interface(s) HID trouvee(s) pour le Seiren V3 Chroma." % len(items))

    def connect(self):
        idx = self.dev_combo.current()
        if idx < 0 or idx >= len(self.interfaces):
            messagebox.showwarning("Connexion", "Selectionne d'abord une interface.")
            return
        if self.dev:
            try:
                self.dev.close()
            except Exception:
                pass
        path = self.interfaces[idx]["path"]
        try:
            self.dev = hid.device()
            self.dev.open_path(path)
            self.dev_path = path
            self.status_lbl.config(text="Connecte (if#%s)" % self.interfaces[idx]["interface_number"],
                                   foreground="green")
            self.log_msg("[OK] Connecte a %s" % path)
        except Exception as e:
            self.dev = None
            self.status_lbl.config(text="Echec connexion", foreground="red")
            self.log_msg("[ERREUR] open_path : %s" % e)

    # --------------------------------------------------------------------- #
    #  Envoi / reception bas niveau
    # --------------------------------------------------------------------- #
    def send_and_read(self, report, label="", read=True, tid=None):
        if not self.dev:
            self.log_msg("[!] Pas connecte. Clique 'Connecter'.")
            return None
        if tid is None:
            tid = self.get_tid()
        try:
            n = self.dev.send_feature_report(bytes([0x00]) + bytes(report))
        except Exception as e:
            self.log_msg("[ERREUR envoi] %s : %s" % (label, e))
            return None
        self.log_msg(">> %-22s tid=0x%02X  [%s]" % (label, tid, hexdump(report[:12]) + " ..."))
        if not read:
            return None
        time.sleep(0.05)
        try:
            resp = self.dev.get_feature_report(0x00, 91)
        except Exception as e:
            self.log_msg("   (pas de reponse lisible : %s)" % e)
            return None
        if not resp or len(resp) < 9:
            self.log_msg("   (reponse vide)")
            return None
        payload = resp[1:] if len(resp) >= 91 else resp
        status = payload[0]
        self.log_msg("   << status=0x%02X (%s)  args=[%s]" % (
            status, STATUS.get(status, "?"), hexdump(payload[8:16])))
        return payload

    # --------------------------------------------------------------------- #
    #  Actions diagnostic
    # --------------------------------------------------------------------- #
    def get_firmware(self):
        p = self.send_and_read(cmd_get_firmware(self.get_tid()), "Get Firmware")
        if p and p[0] == 0x02:
            self.log_msg("   ==> Firmware v%d.%d  (transaction_id CORRECT !)" % (p[8], p[9]))

    def get_serial(self):
        p = self.send_and_read(cmd_get_serial(self.get_tid()), "Get Serial")
        if p and p[0] == 0x02:
            serial = bytes(p[8:8 + 22]).split(b"\x00")[0].decode("ascii", "replace")
            self.log_msg("   ==> Serial : %s" % serial)

    def sweep_transaction_ids(self):
        """Teste chaque transaction_id avec Get Firmware et signale ceux qui repondent SUCCESS."""
        if not self.dev:
            self.log_msg("[!] Pas connecte.")
            return
        self.log_msg("=== SWEEP transaction_id (via Get Firmware) ===")
        winners = []
        for tid in TRANSACTION_IDS:
            p = self.send_and_read(cmd_get_firmware(tid), "FW tid=0x%02X" % tid, tid=tid)
            if p and p[0] == 0x02:
                winners.append(tid)
                self.log_msg("   *** tid=0x%02X => SUCCESS (fw v%d.%d) ***" % (tid, p[8], p[9]))
            time.sleep(0.03)
        if winners:
            self.log_msg("=== GAGNANT(S) : %s ===" % ", ".join("0x%02X" % t for t in winners))
            # selectionne automatiquement le premier gagnant
            self.tid_combo.set("0x%02X" % winners[0])
        else:
            self.log_msg("=== Aucun transaction_id n'a repondu SUCCESS sur cette interface. ===")
            self.log_msg("    -> Essaie une autre interface HID (Rafraichir/Connecter) si dispo.")

    # --------------------------------------------------------------------- #
    #  Actions lumiere
    # --------------------------------------------------------------------- #
    def send_static(self):
        self.send_and_read(cmd_static(self.get_proto(), self.get_varstore(),
                                      self.get_led(), self.color, self.get_tid()),
                           "STATIC %s" % self.get_proto())

    def send_off(self):
        self.send_and_read(cmd_off(self.get_proto(), self.get_varstore(),
                                   self.get_led(), self.get_tid()), "OFF")

    def send_brightness(self, level):
        self.send_and_read(cmd_brightness(self.get_proto(), self.get_varstore(),
                                          self.get_led(), level, self.get_tid()),
                           "Brightness=0x%02X" % level)

    def send_led_on(self):
        self.send_and_read(cmd_led_state(self.get_varstore(), self.get_led(), 0x01, self.get_tid()),
                           "LED State ON")

    def send_custom_frame(self):
        try:
            n = max(1, min(80, int(self.nleds_entry.get())))
        except ValueError:
            self.log_msg("[!] Nb LEDs invalide.")
            return
        rgb_list = [self.color] * n
        proto = self.get_proto()
        self.send_and_read(cmd_custom_frame(proto, 0, 0, n - 1, rgb_list, self.get_tid()),
                           "Custom frame (%d LEDs)" % n, read=False)
        if proto == PROTO_STANDARD:
            # Sur les devices standard il faut activer le mode "custom"
            self.send_and_read(cmd_effect_custom_standard(self.get_tid()),
                               "Effect=CUSTOM", read=False)
        self.log_msg("   -> Regarde le micro : combien de LEDs se sont allumees ?")


def main():
    root = tk.Tk()
    ProbeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
