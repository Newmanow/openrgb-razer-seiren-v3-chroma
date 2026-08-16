#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seiren V3 Chroma - Controleur RGB (interface graphique)
=======================================================
Logiciel autonome pour piloter l'eclairage du Razer Seiren V3 Chroma sous Windows,
SANS Razer Synapse. Utilise le protocole reverse-engineere (voir seiren.py).

Lancer :  python seiren_controller.py
Dependance :  pip install hidapi
"""
import colorsys
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

from seiren import SeirenV3Chroma, SeirenError

NUM_LEDS = 16  # taille de la rangee adressable (cf. retro-ingenierie)


class ControllerApp:
    def __init__(self, root):
        self.root = root
        self.dev = None
        self.static_color = (0, 255, 255)          # cyan par defaut
        self.led_colors = [(0, 0, 0)] * NUM_LEDS    # mode personnalise
        self.anim_running = False
        self.anim_phase = 0

        root.title("Razer Seiren V3 Chroma — Controleur RGB")
        root.geometry("640x560")
        root.resizable(False, False)

        self._build_header()
        self._build_static()
        self._build_brightness()
        self._build_effects()
        self._build_perled()
        self._build_status()

        self.connect()

    # ------------------------------------------------------------------ UI --
    def _build_header(self):
        f = ttk.LabelFrame(self.root, text="Peripherique")
        f.pack(fill="x", padx=10, pady=6)
        self.dev_lbl = ttk.Label(f, text="Recherche...", font=("Segoe UI", 10, "bold"))
        self.dev_lbl.grid(row=0, column=0, padx=8, pady=4, sticky="w")
        ttk.Button(f, text="Reconnecter", command=self.connect).grid(row=0, column=1, padx=8)

    def _build_static(self):
        f = ttk.LabelFrame(self.root, text="Couleur fixe (toutes les LEDs)")
        f.pack(fill="x", padx=10, pady=6)
        self.swatch = tk.Button(f, text="   ", width=8, bg=self._hex(self.static_color),
                                command=self.pick_static)
        self.swatch.grid(row=0, column=0, padx=8, pady=6)
        ttk.Button(f, text="Choisir une couleur...", command=self.pick_static).grid(row=0, column=1, padx=4)
        ttk.Button(f, text="Appliquer", command=self.apply_static).grid(row=0, column=2, padx=4)
        # raccourcis couleurs
        quick = [("Rouge", (255, 0, 0)), ("Vert", (0, 255, 0)), ("Bleu", (0, 0, 255)),
                 ("Blanc", (255, 255, 255)), ("Cyan", (0, 255, 255)), ("Magenta", (255, 0, 255))]
        qf = ttk.Frame(f)
        qf.grid(row=1, column=0, columnspan=3, pady=4)
        for i, (name, c) in enumerate(quick):
            tk.Button(qf, text=name, bg=self._hex(c), width=8,
                      command=lambda c=c: self.apply_static(c)).grid(row=0, column=i, padx=2)

    def _build_brightness(self):
        f = ttk.LabelFrame(self.root, text="Luminosite")
        f.pack(fill="x", padx=10, pady=6)
        self.bright = tk.IntVar(value=255)
        s = ttk.Scale(f, from_=0, to=255, variable=self.bright, command=self._bright_changed)
        s.grid(row=0, column=0, padx=8, pady=6, sticky="we")
        f.columnconfigure(0, weight=1)
        self.bright_lbl = ttk.Label(f, text="255")
        self.bright_lbl.grid(row=0, column=1, padx=8)

    def _build_effects(self):
        f = ttk.LabelFrame(self.root, text="Effets")
        f.pack(fill="x", padx=10, pady=6)
        ttk.Button(f, text="Spectrum", command=self.apply_spectrum).grid(row=0, column=0, padx=4, pady=6)
        ttk.Button(f, text="Vague", command=self.apply_wave).grid(row=0, column=1, padx=4)
        ttk.Button(f, text="Arc-en-ciel fixe", command=self.apply_rainbow).grid(row=0, column=2, padx=4)
        self.anim_btn = ttk.Button(f, text="Rotation arc-en-ciel ▶", command=self.toggle_anim)
        self.anim_btn.grid(row=0, column=3, padx=4)
        ttk.Button(f, text="Eteindre", command=self.apply_off).grid(row=0, column=4, padx=4)

    def _build_perled(self):
        f = ttk.LabelFrame(self.root, text="Mode personnalise (par LED)")
        f.pack(fill="x", padx=10, pady=6)
        self.led_btns = []
        grid = ttk.Frame(f)
        grid.pack(pady=4)
        for i in range(NUM_LEDS):
            b = tk.Button(grid, text=str(i), width=3, bg=self._hex(self.led_colors[i]),
                          fg="white", command=lambda i=i: self.pick_led(i))
            b.grid(row=i // 8, column=i % 8, padx=2, pady=2)
            self.led_btns.append(b)
        bar = ttk.Frame(f)
        bar.pack(pady=4)
        ttk.Button(bar, text="Appliquer la frame", command=self.apply_perled).grid(row=0, column=0, padx=4)
        ttk.Button(bar, text="Tout effacer", command=self.clear_perled).grid(row=0, column=1, padx=4)

    def _build_status(self):
        self.status = ttk.Label(self.root, text="", foreground="gray")
        self.status.pack(fill="x", padx=12, pady=2)

    # --------------------------------------------------------------- helpers --
    @staticmethod
    def _hex(rgb):
        return "#%02x%02x%02x" % rgb

    def set_status(self, msg, ok=True):
        self.status.config(text=msg, foreground=("green" if ok else "red"))

    def ensure_dev(self):
        if self.dev is None:
            self.set_status("Non connecte.", ok=False)
            return False
        return True

    # ------------------------------------------------------------ connexion --
    def connect(self):
        if self.dev:
            try:
                self.dev.close()
            except Exception:
                pass
            self.dev = None
        try:
            self.dev = SeirenV3Chroma().open()
            fw = self.dev.get_firmware()
            serial = self.dev.get_serial()
            self.dev_lbl.config(
                text="Seiren V3 Chroma connecte — firmware v%s.%s — s/n %s" %
                     (fw[0], fw[1], serial) if fw else "Seiren V3 Chroma connecte")
            self.set_status("Connecte.", ok=True)
        except SeirenError as e:
            self.dev = None
            self.dev_lbl.config(text="Non detecte")
            self.set_status(str(e), ok=False)
        except Exception as e:
            self.dev = None
            self.dev_lbl.config(text="Erreur")
            self.set_status("Erreur: %s" % e, ok=False)

    # ----------------------------------------------------------- actions ---- #
    def pick_static(self):
        rgb, _ = colorchooser.askcolor(initialcolor=self._hex(self.static_color))
        if rgb:
            self.static_color = tuple(int(c) for c in rgb)
            self.swatch.config(bg=self._hex(self.static_color))

    def apply_static(self, color=None):
        if not self.ensure_dev():
            return
        self.stop_anim()
        c = color or self.static_color
        if color:
            self.static_color = color
            self.swatch.config(bg=self._hex(color))
        try:
            self.dev.set_static(*c)
            self.set_status("Couleur fixe appliquee : RGB%s" % (c,))
        except Exception as e:
            self.set_status("Erreur: %s" % e, ok=False)

    def _bright_changed(self, _=None):
        lvl = self.bright.get()
        self.bright_lbl.config(text=str(lvl))
        if self.ensure_dev():
            try:
                self.dev.set_brightness(lvl)
            except Exception as e:
                self.set_status("Erreur luminosite: %s" % e, ok=False)

    def apply_spectrum(self):
        if not self.ensure_dev():
            return
        self.stop_anim()
        self.dev.set_spectrum()
        self.set_status("Effet Spectrum.")

    def apply_wave(self):
        if not self.ensure_dev():
            return
        self.stop_anim()
        self.dev.set_wave()
        self.set_status("Effet Vague.")

    def apply_off(self):
        if not self.ensure_dev():
            return
        self.stop_anim()
        self.dev.set_off()
        self.set_status("Eteint.")

    def apply_rainbow(self, phase=0.0):
        if not self.ensure_dev():
            return
        cols = []
        for i in range(NUM_LEDS):
            h = (i / NUM_LEDS + phase) % 1.0
            r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            cols.append((int(r * 255), int(g * 255), int(b * 255)))
        self.dev.set_custom_frame(cols)
        if phase == 0.0:
            self.set_status("Arc-en-ciel fixe.")

    # ---- animation rotation arc-en-ciel ----
    def toggle_anim(self):
        if self.anim_running:
            self.stop_anim()
        else:
            if not self.ensure_dev():
                return
            self.anim_running = True
            self.anim_btn.config(text="Stop ⏹")
            self.set_status("Rotation arc-en-ciel en cours...")
            self._anim_step()

    def stop_anim(self):
        self.anim_running = False
        self.anim_btn.config(text="Rotation arc-en-ciel ▶")

    def _anim_step(self):
        if not self.anim_running or not self.dev:
            return
        self.anim_phase = (self.anim_phase + 0.02) % 1.0
        try:
            self.apply_rainbow(self.anim_phase)
        except Exception as e:
            self.set_status("Erreur animation: %s" % e, ok=False)
            self.stop_anim()
            return
        self.root.after(60, self._anim_step)

    # ---- mode par LED ----
    def pick_led(self, i):
        rgb, _ = colorchooser.askcolor(initialcolor=self._hex(self.led_colors[i]))
        if rgb:
            self.led_colors[i] = tuple(int(c) for c in rgb)
            self.led_btns[i].config(bg=self._hex(self.led_colors[i]))

    def apply_perled(self):
        if not self.ensure_dev():
            return
        self.stop_anim()
        self.dev.set_custom_frame(self.led_colors)
        self.set_status("Frame personnalisee appliquee.")

    def clear_perled(self):
        self.led_colors = [(0, 0, 0)] * NUM_LEDS
        for b in self.led_btns:
            b.config(bg=self._hex((0, 0, 0)))
        if self.ensure_dev():
            self.stop_anim()
            self.dev.set_custom_frame(self.led_colors)
            self.set_status("Frame effacee.")


def main():
    root = tk.Tk()
    app = ControllerApp(root)

    def on_close():
        app.stop_anim()
        if app.dev:
            try:
                app.dev.close()
            except Exception:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
