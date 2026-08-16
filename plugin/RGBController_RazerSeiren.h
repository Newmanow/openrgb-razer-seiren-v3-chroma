/*---------------------------------------------------------*\
| RGBController_RazerSeiren.h                               |
|                                                           |
|   Couche RGBController OpenRGB pour le Razer Seiren V3     |
|   Chroma.                                                 |
|                                                           |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include "RGBController.h"
#include "RazerSeirenController.h"

enum
{
    SEIREN_MODE_DIRECT   = 0,
    SEIREN_MODE_STATIC   = 1,
    SEIREN_MODE_SPECTRUM = 2,
    SEIREN_MODE_WAVE     = 3,
    SEIREN_MODE_OFF      = 4,
    SEIREN_MODE_BREATHING = 5,
};

class RGBController_RazerSeiren : public RGBController
{
public:
    RGBController_RazerSeiren(RazerSeirenController* controller_ptr);
    ~RGBController_RazerSeiren();

    void        SetupZones();
    void        ResizeZone(int zone, int new_size);

    void        DeviceUpdateLEDs();
    void        UpdateZoneLEDs(int zone);
    void        UpdateSingleLED(int led);

    void        DeviceUpdateMode();

private:
    RazerSeirenController* controller;
};
