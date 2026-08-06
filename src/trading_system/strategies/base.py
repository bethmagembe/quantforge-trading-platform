from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    name: str

    @abstractmethod
    def generate_signals(self, bars: pd.DataFrame) -> pd.Series:
        """Return target positions indexed like bars, normally in {-1, 0, 1}."""

    def parameters(self) -> dict[str, object]:
        return {
            key: value
            for key, value in vars(self).items()
            if not key.startswith("_") and key != "name"
        }
