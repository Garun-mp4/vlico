#!/bin/sh
set -eu
umask 077
# Resolve the active release through the same adapter as public requests.
cd "$HOME/public_html"
exec /usr/bin/flock -n "$HOME/.vlico-offers.lock" /usr/bin/python3.11 -c '
import wsgi
from pathlib import Path
from django.core.management import call_command, get_commands
from django.utils import timezone
if "publish_eva_offers" in get_commands():
    call_command("publish_eva_offers", if_changed=True, scheduled=True)
    (Path.home() / ".vlico-offers-heartbeat").write_text(timezone.now().isoformat())
'
