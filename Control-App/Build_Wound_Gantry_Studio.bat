@echo off
setlocal
set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
set "HERE=%~dp0"

if not exist "%CSC%" (
  echo Microsoft C# compiler was not found.
  pause
  exit /b 1
)

"%CSC%" /nologo /target:winexe /optimize+ /win32manifest:"%HERE%WoundGantryStudio.manifest" /out:"%HERE%WoundGantryStudio.exe" /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll "%HERE%WoundGantryControlApp.cs"

if errorlevel 1 (
  echo.
  echo Build failed.
  pause
  exit /b 1
)

echo WoundGantryStudio.exe built successfully.
pause
