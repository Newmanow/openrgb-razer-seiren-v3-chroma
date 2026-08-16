# Plugin OpenRGB — Razer Seiren V3 Chroma

Ce plugin ajoute le support RGB du **Razer Seiren V3 Chroma** (USB `1532:056F`) à
OpenRGB **sans recompiler OpenRGB**. Une fois compilé, tu déposes le fichier
`RazerSeirenChroma.dll` dans le dossier des plugins, et le micro apparaît dans
OpenRGB comme n'importe quel appareil natif (modes Direct, Static, Spectrum,
Wave, Off + contrôle par-LED des 16 LEDs de l'anneau).

Le protocole a été rétro-ingénieré : feature report ID `0x07`, paquet
`razer_report` compact de 63 octets, `transaction_id` `0x1F`, commandes
« Extended Matrix » (classe `0x0F`). Voir `../seiren.py` pour la version Python.

---

## ⚠️ La contrainte n°1 : faire correspondre Qt + le compilateur

Un plugin OpenRGB ne se charge **que** s'il est compilé avec la **même version
majeure de Qt** et le **même compilateur** que ton OpenRGB. Sinon OpenRGB refuse
de le charger (sans message clair).

**Vérifie la version de Qt de ton OpenRGB** : regarde les DLL à côté de
`OpenRGB.exe` :
- `Qt5Core.dll` présent → ton OpenRGB est en **Qt 5** → compile le plugin en Qt 5.
- `Qt6Core.dll` présent → ton OpenRGB est en **Qt 6** → compile le plugin en Qt 6.

Les builds officiels Windows utilisent **MSVC** (Visual Studio), pas MinGW :
- Qt **5.15.x** avec **MSVC 2019** (64-bit), ou
- Qt **6.8.x** avec **MSVC 2022** (64-bit).

> 💡 Le plus sûr : compiler le plugin avec exactement la même version de Qt que
> celle affichée dans **OpenRGB → onglet Information/Settings** (ou via les DLL).

---

## Étape 1 — Installer les outils (une seule fois)

1. **Visual Studio 2019 ou 2022 Community** (gratuit) → coche le composant
   *« Développement Desktop en C++ »* (MSVC + Windows SDK).
   https://visualstudio.microsoft.com/fr/downloads/

2. **Qt** via le *Qt Online Installer* :
   https://www.qt.io/download-open-source
   - Coche la version qui correspond à ton OpenRGB, ex. **Qt 5.15.2 → MSVC 2019 64-bit**
     (ou **Qt 6.8.x → MSVC 2022 64-bit**).
   - Coche aussi **Qt Creator** (l'IDE, le plus simple pour compiler).
   - Pour Qt 6, coche également le module **Qt 5 Compatibility Module**.

---

## Étape 2 — Récupérer le code + les sources OpenRGB

Le plugin a besoin des sources d'OpenRGB dans un sous-dossier `OpenRGB/`.

Ouvre un terminal **dans ce dossier `plugin/`** et lance :

```bat
git init
git submodule add https://gitlab.com/CalcProgrammer1/OpenRGB.git OpenRGB
cd OpenRGB
git submodule update --init --recursive
cd ..
```

> Si tu ne veux pas de git : clone simplement OpenRGB et copie-le dans un
> sous-dossier nommé `OpenRGB` ici (il faut que `OpenRGB/dependencies/hidapi-win/`
> existe — il est fourni dans le dépôt OpenRGB).

Arborescence attendue :

```
plugin/
├─ RazerSeirenChroma.pro
├─ RazerSeirenController.{h,cpp}
├─ RGBController_RazerSeiren.{h,cpp}
├─ RazerSeirenPlugin.{h,cpp}
├─ RazerSeirenPlugin.json
└─ OpenRGB/            ← sources OpenRGB (sous-module)
```

---

## Étape 3 — Compiler

### Option A — Qt Creator (recommandé, le plus simple)

1. Lance **Qt Creator** → *Fichier → Ouvrir un fichier ou projet…* →
   sélectionne `RazerSeirenChroma.pro`.
2. Choisis le **Kit** correspondant (ex. *Desktop Qt 5.15.2 MSVC2019 64bit*).
3. En bas à gauche, passe en mode **Release**.
4. Clique sur **Construire** (le marteau 🔨).
5. Le fichier `RazerSeirenChroma.dll` est généré dans le dossier de build
   (ex. `release/`).

### Option B — Ligne de commande

Ouvre l'invite **« x64 Native Tools Command Prompt for VS »**, puis :

```bat
cd chemin\vers\plugin
set PATH=C:\Qt\5.15.2\msvc2019_64\bin;%PATH%
qmake RazerSeirenChroma.pro
nmake release
```

(`RazerSeirenChroma.dll` se trouve alors dans `release\`.)

---

## Étape 4 — Installer le plugin

Copie `RazerSeirenChroma.dll` dans le dossier des plugins d'OpenRGB :

```
%APPDATA%\OpenRGB\plugins\
```

(Crée le dossier `plugins` s'il n'existe pas. Chemin réel typique :
`C:\Users\<toi>\AppData\Roaming\OpenRGB\plugins\`.)

---

## Étape 5 — Vérifier

1. **Ferme** Razer Synapse s'il tourne (il peut monopoliser le périphérique).
2. Lance **OpenRGB**.
3. Onglet **Settings → Plugins** : « Razer Seiren V3 Chroma » doit être listé.
4. Onglet **Devices** : le micro apparaît. Teste une couleur / un effet.

---

## Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| Le plugin n'apparaît pas dans la liste | Mauvaise version de Qt/compilateur → recompile avec la version exacte de ton OpenRGB. |
| `hidapi.dll introuvable` au chargement | Vérifie que `hidapi.dll` est bien à côté de `OpenRGB.exe` (il l'est dans les builds officiels). |
| Le micro est détecté mais ne s'allume pas | Ferme Razer Synapse. Vérifie que le micro est bien sur `1532:056F` (interface `0xFF53`). |
| Erreurs de compilation sur des fichiers `OpenRGB/...` | Le sous-module OpenRGB est incomplet → relance `git submodule update --init --recursive` dans `OpenRGB/`. |
| `usage_page` toujours à 0 / détection rate | Le define `USE_HID_USAGE` doit être actif (il l'est dans le `.pro`). |

---

## Note pour une contribution officielle

Ce code peut servir de base à une vraie intégration dans le cœur d'OpenRGB
(dossier `Controllers/RazerController` adapté pour le format 63 octets) et à
fermer l'issue [openrazer #2640](https://github.com/openrazer/openrazer/issues/2640).
