@echo off
rem Record fit 2 chain (docs/RECORD_FIT_2.md): wave 5, the ensemble, the candidate and the
rem validation on the fresh seeds 9112-9159, without a pause. Run from the repo root, after
rem scripts\record_fit2.py --replay. Needs CRLF line endings (cmd mis-seeks labels in LF files).
setlocal
set PYTHONPATH=%~dp0..\src
cd /d %~dp0..
if not defined U25_PY set U25_PY=python
set LOG=_output\hm_record2
if not exist %LOG% mkdir %LOG%
del /q %LOG%\chain.done 2>nul
(echo wave 5)> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit2.py --wave 5 --n 120 --workers 10 > %LOG%\wave5.log 2>&1 || goto fail
echo ensemble> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit2.py --mix-ensemble --workers 10 > %LOG%\ensemble.log 2>&1 || goto fail
echo write ensemble> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit2.py --write-ensemble configs\record_fit2_ensemble.json > %LOG%\write_ensemble.log 2>&1 || goto fail
echo candidate> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\record_fit2.py --candidate configs\record_fit2_ensemble.json > %LOG%\candidate.log 2>&1 || goto fail
echo validate candidate> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\replica_validate.py --ensemble configs\record_fit2_candidate.json --part pen --pen-seeds 9112-9159 --label record_fit2 --adults-131 --workers 10 > %LOG%\validate_candidate.log 2>&1 || goto fail
echo validate final replica> %LOG%\chain.step
%U25_PY% -X utf8 -u scripts\replica_validate.py --ensemble configs\replica_v2_final.json --part pen --pen-seeds 9112-9159 --label record_fit2_final_replica --adults-131 --workers 10 > %LOG%\validate_final_replica.log 2>&1 || goto fail
echo ok> %LOG%\chain.done
exit /b 0
:fail
echo failed> %LOG%\chain.done
exit /b 1
