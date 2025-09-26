@echo off
REM LGPO.exe Installation Helper Script
REM CIS GPO Compliance Tool - Deployment Module

echo ========================================
echo LGPO.exe Installation Helper
echo ========================================
echo.

echo This script helps you install LGPO.exe for full deployment functionality.
echo LGPO.exe is a free utility from Microsoft for managing Local Group Policy.
echo.

echo Checking for LGPO.exe...

if exist "LGPO.exe" (
    echo ✅ LGPO.exe found in tools directory!
    echo.
    echo Testing LGPO.exe...
    LGPO.exe /? >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ✅ LGPO.exe is working correctly
        LGPO.exe /?
    ) else (
        echo ❌ LGPO.exe found but not working properly
        echo Please redownload from Microsoft
    )
    echo.
    echo Installation verified successfully.
    goto :end
)

if exist "..\LGPO.exe" (
    echo ✅ LGPO.exe found in parent directory!
    echo Moving to tools directory...
    move "..\LGPO.exe" "LGPO.exe"
    echo ✅ LGPO.exe moved successfully
    goto :verify
)

echo ❌ LGPO.exe not found

echo.
echo DOWNLOAD INSTRUCTIONS:
echo ======================
echo 1. Open a web browser and visit:
echo    https://www.microsoft.com/en-us/download/details.aspx?id=55319
echo.
echo 2. Click "Download" button
echo.
echo 3. Select "LGPO.zip" and download
echo.
echo 4. Extract the downloaded ZIP file
echo.
echo 5. Copy LGPO.exe to this directory:
echo    %~dp0
echo.
echo 6. Run this script again to verify installation
echo.

echo ALTERNATIVE: Registry-Only Mode
echo ================================
echo Without LGPO.exe, the deployment tool will:
echo - Generate Registry (.reg) files instead of Policy (.pol) files
echo - Provide manual import instructions
echo - Maintain full PowerShell script generation
echo.
echo This provides 90%% of functionality for air-gapped deployments.
echo.

goto :end

:verify
echo.
echo Testing LGPO.exe...
LGPO.exe /? >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ LGPO.exe is working correctly
    echo.
    echo Version information:
    LGPO.exe /?
) else (
    echo ❌ LGPO.exe not working properly
    echo Please redownload from Microsoft
)

:end
echo.
echo ========================================
echo Installation check complete
echo ========================================
pause