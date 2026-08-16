#-----------------------------------------------------------------------------#
# Razer Seiren V3 Chroma - Plugin OpenRGB (QMake)                              #
#                                                                             #
# Les sources OpenRGB sont partagees a la racine du projet : ../../OpenRGB     #
#-----------------------------------------------------------------------------#

QT          += core gui widgets

if(greaterThan(QT_MAJOR_VERSION, 5)) {
    QT += core5compat
}

TEMPLATE    = lib
CONFIG      += plugin c++17 silent
TARGET      = RazerSeirenChroma

ORGB        = $$PWD/../../OpenRGB

#-----------------------------------------------------------------------------#
# Version                                                                     #
#-----------------------------------------------------------------------------#
VERSION_STR     = "1.0"
GIT_COMMIT_ID   = $$system(git log -n 1 --pretty=format:"%H")
GIT_COMMIT_DATE = $$system(git log -n 1 --pretty=format:"%ci")
win32:BUILDDATE = $$system(date /t)

DEFINES +=                                                                     \
    VERSION_STRING=\\"\"\"$$VERSION_STR\\"\"\"                                 \
    GIT_COMMIT_ID=\\"\"\"$$GIT_COMMIT_ID\\"\"\"                                \
    GIT_COMMIT_DATE=\\"\"\"$$GIT_COMMIT_DATE\\"\"\"                            \
    BUILDDATE_STRING=\\"\"\"$$BUILDDATE\\"\"\"

#-----------------------------------------------------------------------------#
# OpenRGB Plugin SDK (source partagee dans ../../OpenRGB)                      #
#-----------------------------------------------------------------------------#
INCLUDEPATH +=                                                                 \
    $$ORGB                                                                     \
    $$ORGB/RGBController                                                       \
    $$ORGB/dependencies/json                                                   \
    $$ORGB/qt                                                                  \
    $$ORGB/i2c_smbus                                                           \
    $$ORGB/net_port                                                            \

HEADERS +=                                                                     \
    $$ORGB/OpenRGBPluginInterface.h                                            \
    $$ORGB/ResourceManagerInterface.h                                          \
    $$ORGB/RGBController/RGBController.h                                        \
    RazerSeirenController.h                                                    \
    RGBController_RazerSeiren.h                                                \
    RazerSeirenPlugin.h                                                        \

SOURCES +=                                                                     \
    $$ORGB/RGBController/RGBController.cpp                                      \
    $$ORGB/LogManager.cpp                                                      \
    $$ORGB/qt/hsv.cpp                                                          \
    RazerSeirenController.cpp                                                  \
    RGBController_RazerSeiren.cpp                                              \
    RazerSeirenPlugin.cpp                                                      \

DISTFILES +=                                                                   \
    RazerSeirenPlugin.json                                                     \
    README.md                                                                  \

#-----------------------------------------------------------------------------#
# hidapi (Windows : prebuilt fourni avec OpenRGB)                             #
#-----------------------------------------------------------------------------#
win32 {
    INCLUDEPATH += $$ORGB/dependencies/hidapi-win/include
    DEFINES     += USE_HID_USAGE

    contains(QMAKE_TARGET.arch, x86_64) {
        LIBS += -L"$$ORGB/dependencies/hidapi-win/x64/" -lhidapi
    } else {
        LIBS += -L"$$ORGB/dependencies/hidapi-win/x86/" -lhidapi
    }
}

#-----------------------------------------------------------------------------#
# hidapi (Linux : paquet systeme)                                            #
#-----------------------------------------------------------------------------#
unix:!macx {
    CONFIG  += link_pkgconfig
    DEFINES += USE_HID_USAGE
    packagesExist(hidapi-hidraw) {
        PKGCONFIG += hidapi-hidraw
    } else {
        PKGCONFIG += hidapi
    }
}
