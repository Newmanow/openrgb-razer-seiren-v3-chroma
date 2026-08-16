/*---------------------------------------------------------*\
| RGBController_RazerSeiren.cpp                             |
|                                                           |
|   Couche RGBController OpenRGB pour le Razer Seiren V3     |
|   Chroma.                                                 |
|                                                           |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include "RGBController_RazerSeiren.h"
#include <vector>

/**------------------------------------------------------------------*\
    @name Razer Seiren V3 Chroma
    @type USB
    @save :x:
    @direct :white_check_mark:
    @effects :white_check_mark:
    @detectors DetectRazerSeiren
    @comment Protocole reverse-engineere (report ID 0x07, paquet 63 octets).
\*-------------------------------------------------------------------*/

RGBController_RazerSeiren::RGBController_RazerSeiren(RazerSeirenController* controller_ptr)
{
    controller  = controller_ptr;

    name        = "Razer Seiren V3 Chroma";
    vendor      = "Razer";
    type        = DEVICE_TYPE_MICROPHONE;
    description = "Razer Seiren V3 Chroma microphone";
    version     = controller->GetFirmwareString();
    serial      = controller->GetSerialString();
    location    = controller->GetLocationString();

    /*-----------------------------------------------------*\
    | Mode Direct (controle par-LED)                        |
    \*-----------------------------------------------------*/
    mode Direct;
    Direct.name       = "Direct";
    Direct.value      = SEIREN_MODE_DIRECT;
    Direct.flags      = MODE_FLAG_HAS_PER_LED_COLOR | MODE_FLAG_HAS_BRIGHTNESS;
    Direct.color_mode = MODE_COLORS_PER_LED;
    Direct.brightness_min = 0;
    Direct.brightness_max = 255;
    Direct.brightness     = 255;
    modes.push_back(Direct);

    /*-----------------------------------------------------*\
    | Mode Static (couleur unique materielle)               |
    \*-----------------------------------------------------*/
    mode Static;
    Static.name       = "Static";
    Static.value      = SEIREN_MODE_STATIC;
    Static.flags      = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR | MODE_FLAG_HAS_BRIGHTNESS;
    Static.color_mode = MODE_COLORS_MODE_SPECIFIC;
    Static.colors_min = 1;
    Static.colors_max = 1;
    Static.colors.resize(1);
    Static.brightness_min = 0;
    Static.brightness_max = 255;
    Static.brightness     = 255;
    modes.push_back(Static);

    /*-----------------------------------------------------*\
    | Mode Spectrum                                         |
    \*-----------------------------------------------------*/
    mode Spectrum;
    Spectrum.name       = "Spectrum Cycle";
    Spectrum.value      = SEIREN_MODE_SPECTRUM;
    Spectrum.flags      = 0;
    Spectrum.color_mode = MODE_COLORS_NONE;
    modes.push_back(Spectrum);

    /*-----------------------------------------------------*\
    | Mode Wave                                             |
    \*-----------------------------------------------------*/
    mode Wave;
    Wave.name       = "Wave";
    Wave.value      = SEIREN_MODE_WAVE;
    Wave.flags      = MODE_FLAG_HAS_SPEED | MODE_FLAG_HAS_DIRECTION_LR;
    Wave.color_mode = MODE_COLORS_NONE;
    Wave.speed_min  = 0x0A;
    Wave.speed_max  = 0x50;
    Wave.speed      = 0x28;
    Wave.direction  = MODE_DIRECTION_LEFT;
    modes.push_back(Wave);

    /*-----------------------------------------------------*\
    | Mode Breathing (respiration, couleur unique)          |
    \*-----------------------------------------------------*/
    mode Breathing;
    Breathing.name       = "Breathing";
    Breathing.value      = SEIREN_MODE_BREATHING;
    Breathing.flags      = MODE_FLAG_HAS_MODE_SPECIFIC_COLOR;
    Breathing.color_mode = MODE_COLORS_MODE_SPECIFIC;
    Breathing.colors_min = 1;
    Breathing.colors_max = 1;
    Breathing.colors.resize(1);
    modes.push_back(Breathing);

    /*-----------------------------------------------------*\
    | Mode Off                                              |
    \*-----------------------------------------------------*/
    mode Off;
    Off.name       = "Off";
    Off.value      = SEIREN_MODE_OFF;
    Off.flags      = 0;
    Off.color_mode = MODE_COLORS_NONE;
    modes.push_back(Off);

    SetupZones();

    /*-----------------------------------------------------*\
    | Mode Direct actif par defaut (pour les effets OpenRGB)|
    \*-----------------------------------------------------*/
    active_mode = 0;
}

RGBController_RazerSeiren::~RGBController_RazerSeiren()
{
    delete controller;
}

void RGBController_RazerSeiren::SetupZones()
{
    zone underglow;
    underglow.name       = "Underglow";
    underglow.type       = ZONE_TYPE_LINEAR;
    underglow.leds_min   = SEIREN_NUM_LEDS;
    underglow.leds_max   = SEIREN_NUM_LEDS;
    underglow.leds_count = SEIREN_NUM_LEDS;
    underglow.matrix_map = NULL;
    zones.push_back(underglow);

    for(unsigned int i = 0; i < SEIREN_NUM_LEDS; i++)
    {
        led new_led;
        new_led.name = "LED " + std::to_string(i + 1);
        leds.push_back(new_led);
    }

    SetupColors();
}

void RGBController_RazerSeiren::ResizeZone(int /*zone*/, int /*new_size*/)
{
    /*-----------------------------------------------------*\
    | Zone de taille fixe : rien a faire                    |
    \*-----------------------------------------------------*/
}

void RGBController_RazerSeiren::DeviceUpdateLEDs()
{
    /*-----------------------------------------------------*\
    | Pousse le buffer de couleurs vers la custom frame     |
    \*-----------------------------------------------------*/
    std::vector<unsigned char> rgb_data;
    rgb_data.reserve(colors.size() * 3);

    for(std::size_t i = 0; i < colors.size(); i++)
    {
        rgb_data.push_back((unsigned char)RGBGetRValue(colors[i]));
        rgb_data.push_back((unsigned char)RGBGetGValue(colors[i]));
        rgb_data.push_back((unsigned char)RGBGetBValue(colors[i]));
    }

    controller->SetCustomFrame(rgb_data);
}

void RGBController_RazerSeiren::UpdateZoneLEDs(int /*zone*/)
{
    DeviceUpdateLEDs();
}

void RGBController_RazerSeiren::UpdateSingleLED(int /*led*/)
{
    DeviceUpdateLEDs();
}

void RGBController_RazerSeiren::DeviceUpdateMode()
{
    const mode& m = modes[active_mode];

    switch(m.value)
    {
        case SEIREN_MODE_DIRECT:
            controller->SetBrightness((unsigned char)m.brightness);
            DeviceUpdateLEDs();
            break;

        case SEIREN_MODE_STATIC:
        {
            controller->SetBrightness((unsigned char)m.brightness);
            RGBColor c = (m.colors.size() > 0) ? m.colors[0] : 0x00000000;
            controller->SetStatic((unsigned char)RGBGetRValue(c),
                                  (unsigned char)RGBGetGValue(c),
                                  (unsigned char)RGBGetBValue(c));
            break;
        }

        case SEIREN_MODE_BREATHING:
        {
            controller->SetBrightness(0xFF);
            RGBColor c = (m.colors.size() > 0) ? m.colors[0] : 0x00000000;
            controller->SetBreathing((unsigned char)RGBGetRValue(c),
                                     (unsigned char)RGBGetGValue(c),
                                     (unsigned char)RGBGetBValue(c));
            break;
        }

        case SEIREN_MODE_SPECTRUM:
            controller->SetBrightness(0xFF);
            controller->SetSpectrum();
            break;

        case SEIREN_MODE_WAVE:
        {
            unsigned char dir = (m.direction == MODE_DIRECTION_RIGHT) ? 0x01 : 0x00;
            controller->SetBrightness(0xFF);
            controller->SetWave(dir, (unsigned char)m.speed);
            break;
        }

        case SEIREN_MODE_OFF:
            controller->SetOff();
            break;
    }
}
