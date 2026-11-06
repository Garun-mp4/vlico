#!/usr/bin/python3.8
"""Run the adjacent Django WSGI adapter through Apache CGI."""

import sys
from pathlib import Path
from wsgiref.handlers import CGIHandler

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wsgi import application  # noqa: E402

CGIHandler().run(application)
