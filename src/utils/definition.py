from pygame import Rect
from .settings import GameSettings
from dataclasses import dataclass
from enum import Enum
from typing import overload, TypedDict, Protocol

MouseBtn = int
Key = int

Direction = Enum('Direction', ['UP', 'DOWN', 'LEFT', 'RIGHT', 'NONE'])

@dataclass
class Position:
    x: float
    y: float
    
    def copy(self):
        return Position(self.x, self.y)
        
    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        
@dataclass
class PositionCamera:
    x: int
    y: int
    
    def copy(self):
        return PositionCamera(self.x, self.y)
        
    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)
        
    def transform_position(self, position: Position) -> tuple[int, int]:
        return (int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_position_as_position(self, position: Position) -> Position:
        return Position(int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_rect(self, rect: Rect) -> Rect:
        return Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

@dataclass
class Teleport:
    pos: Position
    destination: str
    dest_pos: Position | None = None

    
    @overload
    def __init__(self, x: int, y: int, destination: str) -> None: ...
    @overload
    def __init__(self, pos: Position, destination: str) -> None: ...

    def __init__(self, *args, **kwargs):
        if isinstance(args[0], Position):
            self.pos = args[0]
            self.destination = args[1]
            self.dest_pos = args[2] if len(args) > 2 else None
        else:
            x, y, dest = args[:3]
            dest_x = args[3] if len(args) > 3 else None
            dest_y = args[4] if len(args) > 4 else None
            self.pos = Position(x, y)
            self.destination = dest
            self.dest_pos = Position(dest_x, dest_y) if dest_x is not None and dest_y is not None else None
    
    def to_dict(self):
        data = {
            "x": self.pos.x / GameSettings.TILE_SIZE,
            "y": self.pos.y / GameSettings.TILE_SIZE,
            "destination": self.destination
        }
        if self.dest_pos:
            data["dest_x"] = self.dest_pos.x / GameSettings.TILE_SIZE
            data["dest_y"] = self.dest_pos.y / GameSettings.TILE_SIZE
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        dest_pos = None
        if "dest_x" in data and "dest_y" in data:
            dest_pos = Position(
                data["dest_x"] * GameSettings.TILE_SIZE,
                data["dest_y"] * GameSettings.TILE_SIZE
            )
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            data["destination"],
            dest_pos.x if dest_pos else None,
            dest_pos.y if dest_pos else None
        )
    
class Monster(TypedDict):
    name: str
    hp: int
    max_hp: int
    level: int
    sprite_path: str

class Item(TypedDict):
    name: str
    count: int
    sprite_path: str