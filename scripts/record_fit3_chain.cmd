@echo off
rem Record fit 3 chain (docs/RECORD_FIT_3.md): the 36 selection seeds and the rule, then the
rem validation on fresh seeds, but only if a candidate meets the bar on its 48 training seeds.
rem Run from the repo root, after scripts\record_fit3.py --pool. Needs CRLF line endings.
setlocal
set PYTHONPATH=%~dp0..\src
cd /d %~dp0..
if not defined U25_PY set U25_PY=python
set LOG=_output\hm_record3
if not exist %LOG% mkdir %LOG%
del /q %LOG%\chain.done 2>nul
(echo select)> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit3.py --select --workers 10 > %LOG%\select.log 2>&1
if errorlevel 4 goto fail
if errorlevel 3 goto stop
if errorlevel 1 goto fail
(echo validate)> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit3.py --validate --workers 10 > %LOG%\validate.log 2>&1 || goto fail
(echo ok)> %LOG%\chain.done
exit /b 0
:stop
(echo stopped)> %LOG%\chain.done
exit /b 0
:fail
(echo failed)> %LOG%\chain.done
exit /b 1
