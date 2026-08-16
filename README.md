# Razer Seiren V3 Chroma — support OpenRGB

Micro **Razer Seiren V3 Chroma** (USB `1532:056F`) piloté dans OpenRGB.

## Contenu du dossier

```
Seiren Chroma/
├─ plugin/                       Plugin OpenRGB (C++/Qt) — à compiler
│  ├─ RazerSeirenController.*    Protocole bas niveau (Chroma "extended matrix" compact)
│  ├─ RGBController_RazerSeiren.*  Couche RGBController (modes Static/Breathing/Spectrum/Wave/Direct/Off)
│  ├─ RazerSeirenPlugin.*        Point d'entrée plugin OpenRGB
│  ├─ RazerSeirenChroma.pro      Projet qmake
│  ├─ build.bat                  Compilation (Qt 5.15.2 + VS BuildTools 2022)
│  └─ RazerSeirenPlugin.json
├─ seiren.py / seiren_controller.py   Outil Python + GUI Tkinter (pilotage direct, sans OpenRGB)
├─ razer*.c / razer*.h           Références protocole Razer Chroma
├─ *.py (probes/debug)           Scripts de reverse-engineering
└─ RazerSeirenChroma_plugin_source.txt   Tout le code source du plugin en un seul fichier
```

## Dépendance : source OpenRGB (non incluse)

Le plugin se compile contre les sources d'OpenRGB (non versionnées ici — code tiers GPL).
Construit et testé contre **OpenRGB 1.0rc2** (commit `0fca93e4`).

1. Cloner OpenRGB :
   ```
   git clone https://gitlab.com/CalcProgrammer1/OpenRGB.git
   ```
2. Dans `plugin/RazerSeirenChroma.pro`, ajuster la ligne :
   ```
   ORGB = $$PWD/../../OpenRGB      # -> chemin vers ta copie d'OpenRGB
   ```

## Compiler + installer

Pré-requis Windows : **Qt 5.15.2 (msvc2019_64)** + **VS Build Tools 2022**.

```bat
plugin\build.bat
```
Puis copier `plugin\release\RazerSeirenChroma.dll` dans `%APPDATA%\OpenRGB\plugins\` et redémarrer OpenRGB.

> Une DLL pré-compilée est disponible dans les **Releases** de ce dépôt.
