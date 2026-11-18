@echo off
rem Record fit chain (docs/RECORD_FIT.md): wave 4, the ensemble, the candidate and the
rem validation on the fresh seeds 9416-9463, without a pause. Run from the repo root.
rem Needs CRLF line endings (cmd mis-seeks labels in LF files).
setlocal
set PYTHONPATH=%~dp0..\src
cd /d %~dp0..
if not defined U25_PY set U25_PY=python
set LOG=_output\hm_record
if not exist %LOG% mkdir %LOG%
del /q %LOG%\chain.done 2>nul
echo wave 4> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit.py --wave 4 --n 120 --workers 10 > %LOG%\wave4.log 2>&1 || goto fail
echo ensemble> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit.py --mix-ensemble --workers 10 > %LOG%\ensemble.log 2>&1 || goto fail
echo write ensemble> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit.py --write-ensemble configs\record_fit_ensemble.json > %LOG%\write_ensemble.log 2>&1 || goto fail
echo candidate> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit.py --candidate configs\record_fit_ensemble.json > %LOG%\candidate.log 2>&1 || goto fail
echo validate candidate> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\replica_validate.py --ensemble configs\record_fit_candidate.json --part pen --pen-seeds 9416-9463 --label record_fit --workers 10 > %LOG%\validate_candidate.log 2>&1 || goto fail
echo validate final replica> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\replica_validate.py --ensemble configs\replica_v2_final.json --part pen --pen-seeds 9416-9463 --label record_final_replica --workers 10 > %LOG%\validate_final_replica.log 2>&1 || goto fail
echo ok> %LOG%\chain.done
exit /b 0
:fail
echo failed> %LOG%\chain.done
exit /b 1
