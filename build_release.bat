@echo off
echo ===========================================
echo HYP Otomasyon - Release Build Script
echo ===========================================
echo.

cd /d "%~dp0"

echo [1/4] HYP_Doktor derleniyor...
pyinstaller --clean HYP_Doktor.spec
if errorlevel 1 (
    echo HATA: HYP_Doktor derlenemedi!
    pause
    exit /b 1
)

echo [2/4] HYP_Hemsire derleniyor...
pyinstaller --clean HYP_Hemsire.spec
if errorlevel 1 (
    echo HATA: HYP_Hemsire derlenemedi!
    pause
    exit /b 1
)

echo [3/4] Dosyalar kopyalaniyor...

REM Doktor klasorunu olustur ve dosyalari kopyala
if not exist "dist\HYP_Doktor" mkdir "dist\HYP_Doktor"
copy /Y "dist\HYP_Doktor.exe" "dist\HYP_Doktor\"
copy /Y "dist\HYP_Doktor\README.md" "dist\HYP_Doktor\" 2>nul
copy /Y "dist\HYP_Doktor\KULLANIM_KILAVUZU.md" "dist\HYP_Doktor\" 2>nul
copy /Y "dist\HYP_Doktor\FAQ.md" "dist\HYP_Doktor\" 2>nul

REM Hemsire klasorunu olustur ve dosyalari kopyala
if not exist "dist\HYP_Hemsire" mkdir "dist\HYP_Hemsire"
copy /Y "dist\HYP_Hemsire.exe" "dist\HYP_Hemsire\"
copy /Y "dist\HYP_Hemsire\README.md" "dist\HYP_Hemsire\" 2>nul
copy /Y "dist\HYP_Hemsire\KULLANIM_KILAVUZU.md" "dist\HYP_Hemsire\" 2>nul

echo [4/4] Temizlik...
REM Gereksiz dosyalari kaldir
del /Q "dist\HYP_Doktor.exe" 2>nul
del /Q "dist\HYP_Hemsire.exe" 2>nul

echo.
echo ===========================================
echo BUILD TAMAMLANDI!
echo ===========================================
echo.
echo Dosyalar hazir:
echo   - dist\HYP_Doktor\
echo   - dist\HYP_Hemsire\
echo   - dist\KURULUM_REHBERI.txt
echo.
echo Flash disk icin "dist" klasorunu kopyalayin.
echo.
pause
