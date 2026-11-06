import os
import re
from pathlib import Path
from django.core.wsgi import get_wsgi_application

_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.is_file():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _name, _value = _line.split("=", 1)
        _name, _value = _name.strip(), _value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", _name):
            continue
        if len(_value) >= 2 and _value[0] == _value[-1] and _value[0] in "\"'":
            _value = _value[1:-1]
        os.environ.setdefault(_name, _value)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
