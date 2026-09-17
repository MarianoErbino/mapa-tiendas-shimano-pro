@echo off
REM Arranca server HTTP local + abre el mapa en el browser
cd /d "%~dp0"
echo Sirviendo Mapa Tiendas Shimano PRO en http://localhost:8765/
echo (Cerra esta ventana cuando termines de usar el mapa)
start "" "http://localhost:8765/"
python -m http.server 8765
