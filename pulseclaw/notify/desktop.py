from __future__ import annotations

import logging

from pulseclaw.notify.base import Notifier

log = logging.getLogger(__name__)


class DesktopNotifier(Notifier):
    name = "desktop"

    def send(self, title: str, body: str, url: str | None = None) -> bool:
        try:
            from plyer import notification
            notification.notify(
                title=title[:64],
                message=body[:256],
                app_name="PulseClaw",
                timeout=10,
            )
            return True
        except Exception as e:
            log.warning("desktop notify failed: %s", e)
            return False
