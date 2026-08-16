/*---------------------------------------------------------*\
| RazerSeirenPlugin.cpp                                     |
|                                                           |
|   Plugin OpenRGB ajoutant le support du Razer Seiren V3   |
|   Chroma.                                                 |
|                                                           |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include "RazerSeirenPlugin.h"
#include "RGBController_RazerSeiren.h"
#include "RazerSeirenController.h"
#include "RGBController.h"

#include <algorithm>
#include <string>
#include <hidapi.h>
#include <QLabel>

/*-------------------------------------------------------------*\
| Valeurs injectees par le .pro ; fallback si absentes          |
\*-------------------------------------------------------------*/
#ifndef VERSION_STRING
#define VERSION_STRING "1.0"
#endif
#ifndef GIT_COMMIT_ID
#define GIT_COMMIT_ID  ""
#endif

RazerSeirenPlugin::RazerSeirenPlugin()
{
}

RazerSeirenPlugin::~RazerSeirenPlugin()
{
}

OpenRGBPluginInfo RazerSeirenPlugin::GetPluginInfo()
{
    OpenRGBPluginInfo info;
    info.Name           = "Razer Seiren V3 Chroma";
    info.Description     = "Ajoute le support RGB du microphone Razer Seiren V3 Chroma";
    info.Version        = VERSION_STRING;
    info.Commit         = GIT_COMMIT_ID;
    info.URL            = "";
    info.Location       = OPENRGB_PLUGIN_LOCATION_INFORMATION;
    info.Label          = "Seiren";
    info.TabIconString  = "Seiren";

    return(info);
}

unsigned int RazerSeirenPlugin::GetPluginAPIVersion()
{
    return(OPENRGB_PLUGIN_API_VERSION);
}

/*-------------------------------------------------------------------------*\
| Detecte le Seiren et enregistre un controleur s'il n'est pas deja present |
\*-------------------------------------------------------------------------*/
void RazerSeirenPlugin::DetectAndRegister()
{
    if(RM == nullptr)
    {
        return;
    }

    struct hid_device_info* info = hid_enumerate(SEIREN_VID, SEIREN_PID);
    struct hid_device_info* cur  = info;

    while(cur != nullptr)
    {
        /*-------------------------------------------------*\
        | Seule l'interface vendor 0xFF53 pilote les LEDs   |
        \*-------------------------------------------------*/
        if(cur->usage_page == SEIREN_USAGE_PAGE)
        {
            std::string location = "HID: " + std::string(cur->path);

            /*---------------------------------------------*\
            | Eviter les doublons : deja enregistre ?       |
            \*---------------------------------------------*/
            bool already = false;
            for(RGBController* existing : RM->GetRGBControllers())
            {
                if(existing->GetLocation() == location)
                {
                    already = true;
                    break;
                }
            }

            if(!already)
            {
                hid_device* dev = hid_open_path(cur->path);

                if(dev != nullptr)
                {
                    RazerSeirenController*     controller = new RazerSeirenController(dev, cur->path);
                    RGBController_RazerSeiren* rgb_ctrl   = new RGBController_RazerSeiren(controller);

                    RM->RegisterRGBController(rgb_ctrl);
                    controllers.push_back(rgb_ctrl);
                }
            }
        }
        cur = cur->next;
    }

    if(info != nullptr)
    {
        hid_free_enumeration(info);
    }
}

/*-------------------------------------------------------------------------*\
| Debut de detection (rescan) : OpenRGB s'apprete a detruire (delete) tous   |
| les controleurs de rgb_controllers_hw, dont les notres. On lache nos       |
| references SANS delete (OpenRGB s'en charge) pour eviter un double-free.   |
\*-------------------------------------------------------------------------*/
void RazerSeirenPlugin::OnDetectionStart(void* this_ptr)
{
    RazerSeirenPlugin* self = static_cast<RazerSeirenPlugin*>(this_ptr);
    self->controllers.clear();
}

/*-------------------------------------------------------------------------*\
| Fin de detection : on (re)enregistre le micro.                            |
\*-------------------------------------------------------------------------*/
void RazerSeirenPlugin::OnDetectionEnd(void* this_ptr)
{
    RazerSeirenPlugin* self = static_cast<RazerSeirenPlugin*>(this_ptr);
    self->DetectAndRegister();
}

void RazerSeirenPlugin::Load(ResourceManagerInterface* resource_manager_ptr)
{
    RM = resource_manager_ptr;

    hid_init();

    /*-----------------------------------------------------*\
    | Re-enregistrement automatique a chaque rescan          |
    \*-----------------------------------------------------*/
    RM->RegisterDetectionStartCallback(&RazerSeirenPlugin::OnDetectionStart, this);
    RM->RegisterDetectionEndCallback(&RazerSeirenPlugin::OnDetectionEnd, this);

    /*-----------------------------------------------------*\
    | Enregistrement initial (la detection de demarrage est |
    | deja terminee quand le plugin est charge)             |
    \*-----------------------------------------------------*/
    DetectAndRegister();
}

QWidget* RazerSeirenPlugin::GetWidget()
{
    /*-----------------------------------------------------*\
    | OpenRGB ne verifie pas le nullptr ici : on DOIT        |
    | renvoyer un widget valide, sinon access violation.    |
    \*-----------------------------------------------------*/
    QLabel* widget = new QLabel(
        "Razer Seiren V3 Chroma\n\n"
        "Plugin RGB actif.\n"
        "Pilote le micro depuis l'onglet Devices.");
    widget->setAlignment(Qt::AlignCenter);
    widget->setWordWrap(true);
    return(widget);
}

QMenu* RazerSeirenPlugin::GetTrayMenu()
{
    return(nullptr);
}

void RazerSeirenPlugin::Unload()
{
    if(RM != nullptr)
    {
        RM->UnregisterDetectionStartCallback(&RazerSeirenPlugin::OnDetectionStart, this);
        RM->UnregisterDetectionEndCallback(&RazerSeirenPlugin::OnDetectionEnd, this);

        /*-------------------------------------------------*\
        | Ne supprimer que les controleurs encore presents  |
        | dans la liste d'OpenRGB (les autres ont deja ete  |
        | detruits par Cleanup) -> evite tout double-free.  |
        \*-------------------------------------------------*/
        std::vector<RGBController*>& list = RM->GetRGBControllers();
        for(RGBController* c : controllers)
        {
            if(std::find(list.begin(), list.end(), c) != list.end())
            {
                RM->UnregisterRGBController(c);
                delete c;
            }
        }
    }
    controllers.clear();

    hid_exit();
}
