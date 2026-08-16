/*---------------------------------------------------------*\
| RazerSeirenPlugin.h                                       |
|                                                           |
|   Plugin OpenRGB ajoutant le support du Razer Seiren V3   |
|   Chroma sans recompiler OpenRGB.                         |
|                                                           |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include <QObject>
#include <vector>

#include "OpenRGBPluginInterface.h"
#include "ResourceManagerInterface.h"

class RGBController;

class RazerSeirenPlugin : public QObject, public OpenRGBPluginInterface
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID OpenRGBPluginInterface_IID FILE "RazerSeirenPlugin.json")
    Q_INTERFACES(OpenRGBPluginInterface)

public:
    RazerSeirenPlugin();
    ~RazerSeirenPlugin();

    OpenRGBPluginInfo   GetPluginInfo()                                         override;
    unsigned int        GetPluginAPIVersion()                                   override;

    void                Load(ResourceManagerInterface* resource_manager_ptr)    override;
    QWidget*            GetWidget()                                             override;
    QMenu*              GetTrayMenu()                                           override;
    void                Unload()                                               override;

private:
    ResourceManagerInterface*       RM = nullptr;
    std::vector<RGBController*>      controllers;

    /*-----------------------------------------------------*\
    | Detecte le(s) Seiren et enregistre le(s) controleur(s)|
    | (ignore ceux deja presents pour eviter les doublons). |
    \*-----------------------------------------------------*/
    void                DetectAndRegister();

    /*-----------------------------------------------------*\
    | Callbacks de detection (rescan) : OpenRGB detruit nos |
    | controleurs au debut de chaque detection, il faut les |
    | re-enregistrer a la fin.                              |
    \*-----------------------------------------------------*/
    static void         OnDetectionStart(void* this_ptr);
    static void         OnDetectionEnd(void* this_ptr);
};
