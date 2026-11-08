@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_CMD=python"
if exist ".buildvenv\Scripts\python.exe" set "PYTHON_CMD=%CD%\.buildvenv\Scripts\python.exe"
"%PYTHON_CMD%" -m PyInstaller --version >nul 2>&1 || (echo PyInstaller is missing in %PYTHON_CMD% & exit /b 2)
"%PYTHON_CMD%" -c "import sys; assert sys.version_info >= (3,10)" || exit /b 2
set "DND="
"%PYTHON_CMD%" -c "import tkinterdnd2" >nul 2>&1 && set "DND=--collect-all=tkinterdnd2"
"%PYTHON_CMD%" -m PyInstaller --noconfirm --clean --windowed --onefile --name ResoArcSecretScout --version-file metadata\ResoArcSecretScout.txt %DND% SecretScout.pyw || exit /b 1
"%PYTHON_CMD%" -m PyInstaller --noconfirm --clean --windowed --onefile --name ResoArcLogLantern --version-file metadata\ResoArcLogLantern.txt %DND% LogLantern.pyw || exit /b 1
"%PYTHON_CMD%" -m PyInstaller --noconfirm --clean --windowed --onefile --name ResoArcFileInspector --version-file metadata\ResoArcFileInspector.txt %DND% FileInspector.pyw || exit /b 1
"%PYTHON_CMD%" -c "import hashlib,pathlib; f=sorted(pathlib.Path('dist').glob('ResoArc*.exe')); assert len(f)==3,f; pathlib.Path('dist/SHA256SUMS.txt').write_text(''.join(hashlib.sha256(x.read_bytes()).hexdigest()+'  '+x.name+'\n' for x in f),encoding='ascii'); print('Manifest:',len(f))" || exit /b 1
echo Windows binaries ready in dist. These files are NOT code-signed.
exit /b 0
