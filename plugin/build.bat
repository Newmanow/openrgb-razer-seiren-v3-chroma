@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "PATH=C:\Qt\5.15.2\msvc2019_64\bin;%PATH%"
cd /d "C:\Users\antho\IA MIC\openrgb-razer-seiren\Seiren Chroma\plugin"

echo ===== QMAKE =====
qmake "CONFIG+=release" RazerSeirenChroma.pro
if errorlevel 1 ( echo QMAKE FAILED & exit /b 1 )

echo ===== NMAKE =====
nmake
if errorlevel 1 ( echo NMAKE FAILED & exit /b 1 )

echo ===== DONE =====
