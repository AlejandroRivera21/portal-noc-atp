@echo off
REM tunnel_atp_completo.bat - Tunel consolidado para NOC
REM Grafana, Kibana, Kuwaiba PROD e Inventario (Maqueta)
 
set PLINK_PATH=plink.exe
 
%PLINK_PATH% -ssh martin_rivera@34.122.118.150 -i "C:\Users\MartinRivera\llaves\putty_llaves.ppk" ^
-L 2222:10.128.0.3:22 ^
-L 2223:10.128.0.2:22 ^
-L 8443:172.20.80.100:443 ^
-L 443:172.20.81.100:443 ^
-L 8088:10.128.0.3:8083 ^
-L 8084:10.128.0.10:8084 ^
-L 8444:10.59.10.6:444 ^
-N -v
 
echo.
echo Tuneles establecidos. Accesos disponibles:
echo - Grafana:             https://localhost:8443
echo - Kibana:              https://localhost:8445
echo - Inventario Maqueta:  https://localhost:8444
echo - Kuwaiba PROD:        https://localhost:8088
echo.
echo Tuneles cerrados. Presione cualquier tecla para finalizar...
pause >nul
    