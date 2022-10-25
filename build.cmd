@echo off
python -m venv tts.venv
call .\\tts.venv\\Scripts\\activate
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install --upgrade pip
python -m pip install -r ./requirements.txt
python -m pip install nuitka zstandard orderedset
nuitka --onefile ./pkg/tts.py --include-package=websockets --include-package=mako --include-package=pydoc --include-data-files=tts.venv/Lib/site-packages/azure/cognitiveservices/speech/*.dll=azure/cognitiveservices/speech/
call deactivate
cmd /C "rd /s/q tts.venv"