@echo off
chcp 65001 >nul
echo ============================================
echo  现金流内部抵消工具 - 打包脚本
echo ============================================
echo.

echo 正在打包，请稍候...
py -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "现金流内部抵消工具_v2" ^
    --hidden-import openpyxl ^
    --add-data "cashflow_tool;cashflow_tool" ^
    --add-data "明细;明细" ^
    --distpath .\dist ^
    --workpath .\build ^
    --specpath .\build ^
    --noconfirm ^
    cashflow_tool\__main__.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo  打包完成！
    echo  文件位置: .\dist\现金流内部抵消工具_v2.exe
    echo ============================================
) else (
    echo [错误] 打包失败，请检查错误信息
)

pause
