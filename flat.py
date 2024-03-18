import re
from enum import StrEnum, auto

FREE_COLOR = 'rgba(255, 238, 218, 0.64)'
RESERVED_COLOR = '???'


class Flat:
    class Status(StrEnum):
        AVAILABLE = auto()
        RESERVED = auto()
        SOLD = auto()

        def __str__(self):
            return self.value

        def __repr__(self):
            return self.value

    def __init__(self, label: str, status=Status.AVAILABLE):
        self.label = label
        self.status = status

    def __eq__(self, other):
        return self.label == other.label and self.status == other.status

    def __repr__(self):
        return f"Flat(\"{self.label}\", \"{self.status}\")"


def parse_flat_from_textcolor(label: str, color: str) -> Flat:
    color_numbers: list[float] = [float(x) for x in re.findall("\\d+", color)]
    if len(color_numbers) < 3:
        raise ValueError(f"Не удалось распознать цвет {color}: {color_numbers}")
    if color == FREE_COLOR:
        return Flat(label, Flat.Status.AVAILABLE)
    elif sum(color_numbers[:3]) == 0:
        return Flat(label, Flat.Status.SOLD)
    else:
        return Flat(label, Flat.Status.RESERVED)


def parse_flat_from_text(label: str, status_text: str) -> Flat:
    status_text = status_text.lower()
    if status_text == '':
        return Flat(label, Flat.Status.AVAILABLE)
    if "продан" in status_text:
        return Flat(label, Flat.Status.SOLD)
    if "бронирован" in status_text:
        return Flat(label, Flat.Status.RESERVED)
    raise ValueError(f"Не удалось распознать статус {status_text}")
