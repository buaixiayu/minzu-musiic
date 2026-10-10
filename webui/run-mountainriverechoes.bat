@echo off
chcp 65001 >nul
REM 启动「山河回响 民族音乐」WebUI 并自动打开浏览器 (http://127.0.0.1:8766)
REM 仓库根目录 = 本文件所在目录的上一级
set "ROOT=%~dp0.."
cd /d "%ROOT%"

REM 把 venv 的 Scripts 加入 PATH，确保服务端能找到 ffmpeg / ffprobe
set "PATH=%ROOT%\venv\Scripts;%PATH%"

if not exist "venv\Scripts\python.exe" (
    echo [错误] 未找到 venv\Scripts\python.exe，请先在该仓库目录创建虚拟环境并安装依赖。
    echo   创建方法：在仓库根目录执行  python -m venv venv  然后  venv\Scripts\pip install -r requirements.txt flask
    pause
    exit /b 1
)

REM 端口预检：若 8766 已被占用（服务已在运行），直接打开浏览器，避免重复启动冲突
venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',8766))==0 else 1)"
if not errorlevel 1 (
    echo [提示] 8766 端口已有服务在运行，直接打开浏览器。
    start "" http://127.0.0.1:8766/
    goto :eof
)

REM 启动服务：新窗口显示运行日志，同时写入 webui\server.log 便于排查；关闭该窗口即停止服务
start "山河回响 WebUI" cmd /k "venv\Scripts\python.exe webui\mountainriverechoes.py > run-server.log 2>&1"

REM 等待端口就绪（最多约 60 秒），使用 Python 探测，不依赖系统 curl
set /a tries=0
:wait
venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',8766))==0 else 1)"
if not errorlevel 1 goto :open
set /a tries+=1
if %tries% geq 60 (
    echo [错误] 服务在 60 秒内未就绪，请查看 run-server.log 排查。
    pause
    exit /b 1
)
timeout /t 1 >nul
goto :wait

:open
echo [就绪] 正在打开浏览器 http://127.0.0.1:8766/
start "" http://127.0.0.1:8766/
