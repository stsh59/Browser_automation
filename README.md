For Mac:

1) Create config.py and add your open ai api key
2) brew install portaudio (for mac) - install it system wide (not venv)
3) create venv
4) export CPATH="$(brew --prefix portaudio)/include" (inside venv)
   export LDFLAGS="-L$(brew --prefix portaudio)/lib" (inside venv)
   export ARCHFLAGS="-arch arm64" (inside venv)
5) Upgrade pip and Install PyAudio:
   pip install --upgrade pip
   pip install --no-binary :all: pyaudio
6) python main.py (run the project)


For windows:

1) Create a file named config.py and add your OpenAI API key.
2) Create a virtual environment:
3) Open Command Prompt or PowerShell, then run:
  python -m venv venv
  venv\Scripts\activate

4) Upgrade pip:
  Inside your activated virtual environment, run:
  pip install --upgrade pip

5) Install PyAudio:
  On Windows you generally don’t need to install PortAudio separately since precompiled PyAudio binaries are available. Try:
  pip install pyaudio
  If you encounter errors (e.g., missing build tools), you can use pipwin which downloads precompiled packages:
  pip install pipwin
  pipwin install pyaudio

6) Run your project:
   Finally, execute your application with:
   python main.py

