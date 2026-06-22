# [C5-REAL] Exergy-Maximized
from __future__ import annotations

class Babylon60:
    """
    [C5-REAL] BABYLON-60 Epistemology.
    Eradicates cumulative float rounding errors and decimal approximation entropy.
    Internally stores values as Base-60 scaled integers.
    1.0 = 3600 units.
    """
    SCALE: int = 3600

    __slots__ = ('_value',)

    def __init__(self, value: int | float | 'Babylon60'):
        if isinstance(value, Babylon60):
            self._value = value._value
        elif isinstance(value, int):
            self._value = value * self.SCALE
        elif isinstance(value, float):
            # Escala y trunca para evitar la entropía del flotante
            self._value = int(value * self.SCALE)
        else:
            raise TypeError("Anergía detectada: Tipo incomputable para Babylon-60.")

    @classmethod
    def from_raw(cls, raw_value: int) -> 'Babylon60':
        """Inicializa directamente desde el valor interno escalado."""
        obj = cls.__new__(cls)
        obj._value = raw_value
        return obj

    def to_float(self) -> float:
        """Solo para interfaces externas (Legacy C4-SIM)."""
        return self._value / self.SCALE

    def __add__(self, other: 'Babylon60') -> 'Babylon60':
        if not isinstance(other, Babylon60):
            raise TypeError("Anergía detectada: Imposible sumar Babylon-60 con tipos mixtos.")
        return Babylon60.from_raw(self._value + other._value)

    def __sub__(self, other: 'Babylon60') -> 'Babylon60':
        if not isinstance(other, Babylon60):
            raise TypeError("Anergía detectada.")
        return Babylon60.from_raw(self._value - other._value)

    def __mul__(self, other: 'Babylon60') -> 'Babylon60':
        if not isinstance(other, Babylon60):
            raise TypeError("Anergía detectada.")
        # Se divide entre SCALE para mantener la proporcionalidad Base-60
        return Babylon60.from_raw((self._value * other._value) // self.SCALE)

    def __truediv__(self, other: 'Babylon60') -> 'Babylon60':
        if not isinstance(other, Babylon60):
            raise TypeError("Anergía detectada.")
        if other._value == 0:
            raise ZeroDivisionError("C5-REAL: Colapso matemático por división entre cero.")
        return Babylon60.from_raw((self._value * self.SCALE) // other._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Babylon60):
            return False
        return self._value == other._value

    def __lt__(self, other: 'Babylon60') -> bool:
        return self._value < other._value

    def __le__(self, other: 'Babylon60') -> bool:
        return self._value <= other._value

    def __gt__(self, other: 'Babylon60') -> bool:
        return self._value > other._value

    def __ge__(self, other: 'Babylon60') -> bool:
        return self._value >= other._value

    def __repr__(self) -> str:
        return f"B60({self._value})"

    def __str__(self) -> str:
        return f"B60({self._value // self.SCALE}.{self._value % self.SCALE})"
