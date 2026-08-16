/*---------------------------------------------------------*\
| RazerSeirenController.h                                   |
|                                                           |
|   Pilote bas niveau du Razer Seiren V3 Chroma (1532:056F) |
|   Protocole reverse-engineere : razer_report compact de   |
|   63 octets, HID feature report ID 0x07, transaction_id   |
|   0x1F, jeu de commandes "Extended Matrix" (classe 0x0F). |
|                                                           |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#pragma once

#include <string>
#include <vector>
#include <hidapi.h>

#define SEIREN_VID              0x1532
#define SEIREN_PID              0x056F
#define SEIREN_USAGE_PAGE       0xFF53
#define SEIREN_REPORT_ID        0x07
#define SEIREN_TRANSACTION_ID   0x1F
#define SEIREN_REPORT_SIZE      63          /* taille du razer_report compact     */
#define SEIREN_ZERO_LED         0x00
#define SEIREN_VARSTORE         0x01
#define SEIREN_NUM_LEDS         16          /* rangee adressable (max par paquet) */

class RazerSeirenController
{
public:
    RazerSeirenController(hid_device* dev_handle, const char* path);
    ~RazerSeirenController();

    std::string     GetSerialString();
    std::string     GetFirmwareString();
    std::string     GetLocationString();

    void            SetBrightness(unsigned char level);
    void            SetStatic(unsigned char red, unsigned char green, unsigned char blue);
    void            SetBreathing(unsigned char red, unsigned char green, unsigned char blue);
    void            SetSpectrum();
    void            SetWave(unsigned char direction, unsigned char speed);
    void            SetOff();

    /*-------------------------------------------------------*\
    | rgb_data : R,G,B,R,G,B,... (au plus SEIREN_NUM_LEDS*3) |
    \*-------------------------------------------------------*/
    void            SetCustomFrame(const std::vector<unsigned char>& rgb_data);

private:
    hid_device*     dev;
    std::string     location;
    std::string     firmware;
    std::string     serial;

    /*-------------------------------------------------------*\
    | Construit le paquet, l'envoie, et (optionnel) lit la    |
    | reponse de 63 octets dans response.                     |
    \*-------------------------------------------------------*/
    int             SendPacket(unsigned char  command_class,
                               unsigned char  command_id,
                               unsigned char  data_size,
                               const unsigned char* args,
                               unsigned char  args_len,
                               unsigned char* response);
};
