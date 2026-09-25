from __future__ import annotations

from dataclasses import dataclass, replace


# ajustes usuario
@dataclass(frozen=True)
class Settings:
    background_playback: bool = True
    mini_player: bool = True
    mini_x: int | None = None
    mini_y: int | None = None

    def with_changes(self, **changes) -> "Settings":
        unknown = set(changes) - set(self.__dataclass_fields__)
        if unknown:
            raise KeyError(f"Ajuste desconocido: {', '.join(sorted(unknown))}")
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @staticmethod
    def from_dict(data) -> "Settings":
        defaults = Settings()
        if not isinstance(data, dict):
            return defaults

        def flag(name: str) -> bool:
            value = data.get(name)
            return value if isinstance(value, bool) else getattr(defaults, name)

        def coordinate(name: str) -> int | None:
            value = data.get(name)
            return value if isinstance(value, int) and not isinstance(value, bool) else None

        return Settings(flag("background_playback"), flag("mini_player"), coordinate("mini_x"), coordinate("mini_y"))
