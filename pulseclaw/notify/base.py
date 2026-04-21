from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    name: str

    @abstractmethod
    def send(self, title: str, body: str, url: str | None = None) -> bool:
        ...
