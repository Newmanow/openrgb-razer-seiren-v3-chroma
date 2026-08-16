/*---------------------------------------------------------*\
| RazerSeirenController.cpp                                 |
|                                                           |
|   Pilote bas niveau du Razer Seiren V3 Chroma.            |
|                                                           |
|   SPDX-License-Identifier: GPL-2.0-or-later               |
\*---------------------------------------------------------*/

#include "RazerSeirenController.h"

#include <cstring>
#include <thread>
#include <chrono>

using namespace std::chrono_literals;

RazerSeirenController::RazerSeirenController(hid_device* dev_handle, const char* path)
{
    dev      = dev_handle;
    location = path;

    /*-----------------------------------------------------*\
    | Lit firmware + numero de serie au demarrage           |
    \*-----------------------------------------------------*/
    GetFirmwareString();
    GetSerialString();
}

RazerSeirenController::~RazerSeirenController()
{
    if(dev != nullptr)
    {
        hid_close(dev);
    }
}

std::string RazerSeirenController::GetLocationString()
{
    return("HID: " + location);
}

/*-------------------------------------------------------------------------*\
| Construit un razer_report compact de 63 octets, l'envoie en feature       |
| report (report ID 0x07 prepended => 64 octets), puis lit la reponse.      |
| CRC = XOR des octets [2..60], place en [61].                              |
| Retourne 0 si OK, -1 sinon. response (63 octets) optionnel.              |
\*-------------------------------------------------------------------------*/
int RazerSeirenController::SendPacket(unsigned char  command_class,
                                      unsigned char  command_id,
                                      unsigned char  data_size,
                                      const unsigned char* args,
                                      unsigned char  args_len,
                                      unsigned char* response)
{
    unsigned char report[SEIREN_REPORT_SIZE];
    unsigned char usb_buf[1 + SEIREN_REPORT_SIZE];

    memset(report, 0x00, sizeof(report));

    report[0x00] = 0x00;                    /* status                       */
    report[0x01] = SEIREN_TRANSACTION_ID;   /* transaction_id               */
    report[0x05] = data_size;               /* data_size                    */
    report[0x06] = command_class;           /* command_class                */
    report[0x07] = command_id;              /* command_id                   */

    if(args != nullptr && args_len > 0)
    {
        if(args_len > (SEIREN_REPORT_SIZE - 8 - 2))
        {
            args_len = (SEIREN_REPORT_SIZE - 8 - 2);
        }
        memcpy(&report[0x08], args, args_len);
    }

    /*-----------------------------------------------------*\
    | CRC                                                   |
    \*-----------------------------------------------------*/
    unsigned char crc = 0;
    for(int i = 2; i < 61; i++)
    {
        crc ^= report[i];
    }
    report[0x3D] = crc;                     /* octet 61                     */

    /*-----------------------------------------------------*\
    | Envoi (report ID 0x07 en tete)                        |
    \*-----------------------------------------------------*/
    usb_buf[0] = SEIREN_REPORT_ID;
    memcpy(&usb_buf[1], report, SEIREN_REPORT_SIZE);

    int ret = hid_send_feature_report(dev, usb_buf, sizeof(usb_buf));
    if(ret < 0)
    {
        return(-1);
    }

    /*-----------------------------------------------------*\
    | Lecture de la reponse si demandee                     |
    \*-----------------------------------------------------*/
    if(response != nullptr)
    {
        std::this_thread::sleep_for(40ms);

        unsigned char in_buf[1 + SEIREN_REPORT_SIZE];
        memset(in_buf, 0x00, sizeof(in_buf));
        in_buf[0] = SEIREN_REPORT_ID;

        int rret = hid_get_feature_report(dev, in_buf, sizeof(in_buf));
        if(rret < 0)
        {
            return(-1);
        }
        memcpy(response, &in_buf[1], SEIREN_REPORT_SIZE);
    }

    return(0);
}

std::string RazerSeirenController::GetFirmwareString()
{
    if(!firmware.empty())
    {
        return(firmware);
    }

    unsigned char response[SEIREN_REPORT_SIZE];
    memset(response, 0, sizeof(response));

    /* classe 0x00 / cmd 0x81 : Get Firmware Version */
    if(SendPacket(0x00, 0x81, 0x02, nullptr, 0, response) == 0 && response[0] == 0x02)
    {
        firmware = std::to_string(response[8]) + "." + std::to_string(response[9]);
    }
    return(firmware);
}

std::string RazerSeirenController::GetSerialString()
{
    if(!serial.empty())
    {
        return(serial);
    }

    unsigned char response[SEIREN_REPORT_SIZE];
    memset(response, 0, sizeof(response));

    /* classe 0x00 / cmd 0x82 : Get Serial */
    if(SendPacket(0x00, 0x82, 0x16, nullptr, 0, response) == 0 && response[0] == 0x02)
    {
        char buf[23];
        memcpy(buf, &response[8], 22);
        buf[22] = '\0';
        serial = std::string(buf);
    }
    return(serial);
}

void RazerSeirenController::SetBrightness(unsigned char level)
{
    /* classe 0x0F / cmd 0x04 : extended brightness */
    unsigned char args[3] = { SEIREN_VARSTORE, SEIREN_ZERO_LED, level };
    SendPacket(0x0F, 0x04, 0x03, args, 3, nullptr);
}

void RazerSeirenController::SetStatic(unsigned char red, unsigned char green, unsigned char blue)
{
    /* classe 0x0F / cmd 0x02, effet static (0x01) */
    unsigned char args[9] = { SEIREN_VARSTORE, SEIREN_ZERO_LED, 0x01,
                              0x00, 0x00, 0x01, red, green, blue };
    SendPacket(0x0F, 0x02, 0x09, args, 9, nullptr);
}

void RazerSeirenController::SetBreathing(unsigned char red, unsigned char green, unsigned char blue)
{
    /* classe 0x0F / cmd 0x02, effet breathing (0x02), couleur unique */
    unsigned char args[9] = { SEIREN_VARSTORE, SEIREN_ZERO_LED, 0x02,
                              0x01, 0x00, 0x01, red, green, blue };
    SendPacket(0x0F, 0x02, 0x09, args, 9, nullptr);
}

void RazerSeirenController::SetSpectrum()
{
    /* classe 0x0F / cmd 0x02, effet spectrum (0x03) */
    unsigned char args[6] = { SEIREN_VARSTORE, SEIREN_ZERO_LED, 0x03, 0x00, 0x00, 0x00 };
    SendPacket(0x0F, 0x02, 0x06, args, 6, nullptr);
}

void RazerSeirenController::SetWave(unsigned char direction, unsigned char speed)
{
    /* classe 0x0F / cmd 0x02, effet wave (0x04) */
    unsigned char args[6] = { SEIREN_VARSTORE, SEIREN_ZERO_LED, 0x04,
                              (unsigned char)(direction & 0x01), speed, 0x00 };
    SendPacket(0x0F, 0x02, 0x06, args, 6, nullptr);
}

void RazerSeirenController::SetOff()
{
    /* classe 0x0F / cmd 0x02, effet none (0x00) */
    unsigned char args[6] = { SEIREN_VARSTORE, SEIREN_ZERO_LED, 0x00, 0x00, 0x00, 0x00 };
    SendPacket(0x0F, 0x02, 0x06, args, 6, nullptr);
}

void RazerSeirenController::SetCustomFrame(const std::vector<unsigned char>& rgb_data)
{
    unsigned char num_leds = (unsigned char)(rgb_data.size() / 3);
    if(num_leds > SEIREN_NUM_LEDS)
    {
        num_leds = SEIREN_NUM_LEDS;
    }

    unsigned char args[5 + SEIREN_NUM_LEDS * 3];
    args[0] = 0x00;
    args[1] = 0x00;
    args[2] = 0x00;                         /* row_index            */
    args[3] = 0x00;                         /* start_col            */
    args[4] = (unsigned char)(num_leds - 1);/* stop_col             */
    memcpy(&args[5], rgb_data.data(), num_leds * 3);

    unsigned char data_size = (unsigned char)(5 + num_leds * 3);

    /* classe 0x0F / cmd 0x03 : extended custom frame */
    SendPacket(0x0F, 0x03, data_size, args, data_size, nullptr);
}
