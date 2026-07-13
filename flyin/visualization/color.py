from flyin.domain.enums import ZoneType
from flyin.domain.zone import Zone


class AnsiColor:
    """Utility for ANSI terminal colors."""

    RESET = "\033[0m"
    BOLD = "\033[1m"

    _COLORS: dict[str, str] = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "gray": "\033[90m",
        "grey": "\033[90m",
        "orange": "\033[33m",
        "gold": "\033[33m",
        "brown": "\033[33m",
        "lime": "\033[92m",
    }

    @classmethod
    def paint(cls, text: str, color: str | None, enabled: bool = True) -> str:
        """Return text wrapped in ANSI color codes when possible."""
        if not enabled or color is None:
            return text

        code = cls._COLORS.get(color.lower())
        if code is None:
            return text

        return f"{code}{text}{cls.RESET}"

    @classmethod
    def paint_zone(cls, zone: Zone, enabled: bool = True) -> str:
        """Return a colored zone label."""
        color = zone.color
        if color is None:
            color = cls._default_color_for_type(zone.zone_type)
        return cls.paint(zone.name, color, enabled)

    @classmethod
    def _default_color_for_type(cls, zone_type: ZoneType) -> str | None:
        """Return a default color for a zone type."""
        if zone_type is ZoneType.BLOCKED:
            return "gray"
        if zone_type is ZoneType.RESTRICTED:
            return "red"
        if zone_type is ZoneType.PRIORITY:
            return "cyan"
        return None
