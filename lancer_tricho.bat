@echo off
cd /d "C:\PATH"
call "%USERPROFILE%\Anaconda3\Scripts\activate.bat" %USERPROFILE%\Anaconda3
call conda activate "name_of_your_env"
start cmd /k python tricho-reminder.py
