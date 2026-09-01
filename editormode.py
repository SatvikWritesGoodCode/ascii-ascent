from __future__ import annotations

from typing import TypeVar, Callable
from clear import clear
from time import sleep
from utils import (PaginateUtils, PerlinNoise, StringUtils,
                   IOUtils
                   )
from maps import (
    LevelData, GameMap, LevelDatabase, C,
    MemoryEfficientInfoMsgs, InfoMsgs, BoxPatch, OrganicPatch, Patch,
    Constants, MapCharset, MapCharseq, Lowercase
)
from textwrap import shorten
from sys import stdout
from random import random
from abc import ABC, abstractmethod
from collections import deque, namedtuple

class Hotkeys(dict):

    "Maps hotkeys to their respective characters."

    POSSIBLE_KEYS = ~Lowercase("wasdeqfzyrfch")
    POSSIBLE_CHARS = MapCharset("SF?#*x_@")

    MAX_HOTKEYS = 5

    WIDTH = Constants.X_LEN + 2

    @staticmethod
    def is_hotkey(hotkey: str):

        if isinstance(hotkey, str):
            return len(hotkey) == 1 and hotkey in Hotkeys.POSSIBLE_KEYS

        return False

    @staticmethod
    def is_character(character: str):

        if isinstance(character, str):
            return len(character) == 1 and character in Hotkeys.POSSIBLE_CHARS

        return False

    def __getitem__(self, hotkey: str):

        if not Hotkeys.is_hotkey(hotkey):
            raise ValueError("Invalid hotkey.")

        return super().__getitem__(hotkey)

    def __setitem__(self, hotkey: str, character: str):

        if not Hotkeys.is_hotkey(hotkey):
            raise ValueError("Invalid hotkey.")
        elif not Hotkeys.is_character(character):
            raise ValueError("Invalid character.")
        elif character in self.values():
            raise ValueError("Character already used.")

        if len(self) < Hotkeys.MAX_HOTKEYS:
            super().__setitem__(hotkey, character)

    def __delitem__(self, hotkey: str):

        if not Hotkeys.is_hotkey(hotkey):
            raise ValueError("Invalid hotkey.")

        if hotkey in self:
            super().__delitem__(hotkey)

    def __str__(self):

        hotkey_lst = "\n".join([
            "| {}{}{} |".format(
                hotkey,
                " " * (Hotkeys.WIDTH - 6),
                self[hotkey],
                )
            for hotkey in self
        ])

        return "\n".join(
            [
                "~"*Hotkeys.WIDTH,
                hotkey_lst,
                "~"*Hotkeys.WIDTH
            ]
        )

    def view(self):

        if not self:
            return

        clear()

        stdout.write("Hotkeys:\n")
        stdout.write(str(self) + "\n")
        IOUtils.input("Press [ENTER] to continue. ")

class PlacementUtils:

    FORWARD = {
        "!": "?"
    }

    REVERSE = {val: key for key, val in FORWARD.items()}

    FORWARD, REVERSE = str.maketrans(FORWARD), str.maketrans(REVERSE)

    @staticmethod
    def normalize(char: str, /, *, reverse=False):

        trans = (
            PlacementUtils.REVERSE if reverse
            else PlacementUtils.FORWARD
        )

        return char.translate(trans)

class EditorData: # custom created maps BY USER

    def __init__(self, levels: list[LevelData]=None):

        if levels is None:
            levels = list()

        for level in levels:
            if not isinstance(level, LevelData):
                raise ValueError("Item is not of type LevelData.")

        self.levels = levels

    def rewrite_author(self, new_username: str):

        if 0 < len(new_username) <= LevelData.MAX_AUTHOR_WIDTH:
            for level in self.levels:
                level.author = new_username
        else:
            raise ValueError("Invalid Username")

    def __bool__(self):

        return bool(self.levels)

    def as_database(self):

        return LevelDatabase(self.levels)

    def append(self, level):

        if not isinstance(level, LevelData):
            raise ValueError("Item is not of type LevelData.")

        self.levels.append(level)

    def pop(self, index=-1):
        self.levels.pop(index)

    def copy(self):

        new_levels = [level.copy() for level in self.levels]
        return EditorData(new_levels)

    def __getitem__(self, ind):

        return self.levels[ind]

    def __setitem__(self, ind: int, item: LevelData):

        if not isinstance(item, LevelData):
            raise ValueError("Item is not of type LevelData.")
        self.levels[ind] = item

    def __delitem__(self, ind: int):

        if not isinstance(ind, int):
            raise ValueError(f"{ind} is not a valid index")

        del self.levels[ind]

    def __len__(self):

        return len(self.levels)

    def get_map(self, *, ind=0):

        return PaginateUtils.paginate(
            self.as_database(), header="Select level:", ind=ind)

class BlockCursorLoc:

    BLOCKS = {
        "Main": MapCharseq("SF?#*x_@"),
        "Arrows/Countdown": MapCharseq("<>^V-|123456789"),
        "Transparent": MapCharseq(":'\";,."),
        "Keys": MapCharseq("lLAnNXKk"),
        "Misc": MapCharseq("()[]{}/\\+=$"),
    }

    def __init__(self, _mode_indices: dict=None, _mode=None):

        # Arguments used for copying. Do not initialize with
        # arguments outside of class.

        if _mode_indices is not None:
            self._mode_indices = _mode_indices
        else:
            self._mode_indices = dict.fromkeys(BlockCursorLoc.BLOCKS, 0)

        self._mode = _mode if _mode is not None else "Main"

    def copy(self):

        return BlockCursorLoc(self._mode_indices.copy(), self._mode)

    def __contains__(self, char: str):

        if not isinstance(char, str):
            return False
        elif len(char) != 1:
            return False

        return any(char in string for string in BlockCursorLoc.BLOCKS.values())

    @property
    def mode(self):
        return self._mode

    @property
    def index(self):
        return self._mode_indices[self._mode]

    def lshift_char(self, shift: int):

        self._mode_indices[self._mode] = max(self.index - shift, 0)

    def rshift_char(self, shift: int):

        self._mode_indices[self._mode] = min(
            self.index + shift,
            len(BlockCursorLoc.BLOCKS[self._mode]) - 1
        )

    def lshift_mode(self, shift: int):

        lst = list(BlockCursorLoc.BLOCKS)
        i = lst.index(self._mode)
        self._mode = lst[max(i - shift, 0)]

    def rshift_mode(self, shift: int):

        lst = list(BlockCursorLoc.BLOCKS)
        i = lst.index(self._mode)

        self._mode = lst[min(i + shift, len(lst) - 1)]

    def shift_char(self, move: str):

        match move:
            case ";" | ";;":
                self.lshift_char(len(move))
            case "'" | "''":
                self.rshift_char(len(move))

    def shift_mode(self, move: str):

        match move:
            case "[" | "[[":
                self.lshift_mode(len(move))
            case "]" | "]]":
                self.rshift_mode(len(move))

    def __str__(self):
        return BlockCursorLoc.BLOCKS[self._mode][self.index]

    @property
    def _mode_list(self):
        return [
            (f">[{mode}]< " if mode == self.mode else f"[{mode}] ")
            for mode in BlockCursorLoc.BLOCKS
        ]

    def goto(self, char: str):

        char = PlacementUtils.normalize(char)

        for mode, chars in BlockCursorLoc.BLOCKS.items():

            if char in chars:

                self._mode_indices[mode] = chars.find(char)
                self._mode = mode
                break

        else:
            raise ValueError("Character not found in cursor.")

    def _slice(self, width: int):

        max_num_elements = width // 4

        n = len(BlockCursorLoc.BLOCKS[self._mode])

        if n <= max_num_elements:
            return slice(None, None, None)

        else:

            half = max_num_elements // 2

            min_index = max(0, self.index - half)
            max_index = min(min_index + max_num_elements, n)
            min_index = max(0, max_index - max_num_elements)

            return slice(min_index, max_index + 1, None)

    def _block_list(self, width):
        return [
            (f"`{block}`" if block == str(self) else f" {block} ")
            for block in BlockCursorLoc.BLOCKS[self._mode]
        ][self._slice(width)]

    def block_menu(self, width: int):

        menu = []

        w = width - 2

        menu.append(f"| {' '.join(self._mode_list).ljust(w)} |")

        blocks = StringUtils.fast_distribute(self._block_list(w),
                                             width=w,
                                             )
        menu.append(f"| {blocks} |")

        menu.append("~"*(width+2))

        return "\n".join(menu)

Action = namedtuple("Action", ["attribute", "method"])

class ToolCursorLoc:

    TOOLS = {
        "Line": Action("line_drawer", "draw"),
        "Box": Action("box_drawer", "draw"),
        "Noise": Action("noise_gen", "noise"),
        "Circle": Action("circle_drawer", "draw"),
        "Fill": Action("filler", "fill"),
        "F&R": Action("replacer", "replace"),
        "Reflect": Action("reflector", "reflect"),
    }

    def __init__(self, _index=None):

        self._index = 0 if _index is None else _index

    def copy(self):

        return ToolCursorLoc(self._index)

    @property
    def mode(self):
        return list(ToolCursorLoc.TOOLS)[self._index]

    @property
    def index(self):
        return self._index

    def lshift_tool(self, shift: int):

        self._index = max(self._index - shift, 0)

    def rshift_tool(self, shift: int):

        self._index = min(
            self._index + shift,
            len(ToolCursorLoc.TOOLS) - 1
        )

    def shift_tool(self, move: str):

        match move:
            case "-" | "--":
                self.lshift_tool(len(move))
            case "=" | "==":
                self.rshift_tool(len(move))

    @property
    def _mode_list(self):
        return [
            (f">[{mode}]< " if mode == self.mode else f"[{mode}] ")
            for mode in ToolCursorLoc.TOOLS
        ]

    def tool_menu(self, width: int):

        cols = " ".join(self._mode_list)

        return f"| {cols:<{width-2}} |\n{'~'*(width+2)}"

    def execute(self, editor):

        a = ToolCursorLoc.TOOLS[self.mode]
        getattr(getattr(editor, a.attribute), a.method)()

class EditorContextState:

    def __init__(self, editor: EditorMode, _block_cursor=None, _pointer=None,
                 _clear=None):

        if _block_cursor is None:
            self.block_cursor = editor.block_cursor
        else:
            self.block_cursor = _block_cursor

        self.pointer = (_pointer.copy()
                        if _pointer is not None else editor.pointer.copy())

        self.clear = _clear if _clear is not None else editor.clear

    def apply(self, editor):

        editor.pointer_controller.draw(clearing=True)

        for attr in ["block_cursor", "clear"]:
            setattr(editor, attr, getattr(self, attr))

        editor.pointer = self.pointer.as_normal()
        editor.pointer_controller.draw()

    @classmethod
    def default(cls, editor: EditorMode):

        return cls(None, BlockCursorLoc(), editor.default_pointer,
                   False)

class Command(ABC):

    def __init__(self, editor: EditorMode):

        self.editor = editor
        self.called = False
        self.state = EditorContextState(editor)

    def __call__(self):

        if self.called is False:
            self._store_inverse()
            self._execute()
            self.called = True

        else:
            self._execute()

    @abstractmethod
    def _execute(self):
        ...

    @abstractmethod
    def _store_inverse(self):
        ...

    @abstractmethod
    def undo(self):
        ...

class CharacterCommand(Command):

    def __init__(self, editor: EditorMode, coord: C, new: str):

        super().__init__(editor)

        self.coord = coord
        self.new = new

    def _store_inverse(self):

        self.old = self.editor.map[self.coord]
        self.old_info = self.editor.info.get(self.coord, None)

    def _execute(self):
        self.editor.map[self.coord] = self.new
        self.editor.display[self.coord] = self.new
        self.editor.info.pop(self.coord)

    def undo(self):
        self.editor.map[self.coord] = self.old
        self.editor.display[self.coord] = self.old
        if self.old_info is not None:
            self.editor.info[self.coord] = self.old_info

class PatchCommand(Command): # Implemented [baseclass]

    def __init__(self, editor: EditorMode, patch: Patch):

        super().__init__(editor)
        self.patch = patch

    def _get_inverse_info(self):

        coords = [coord for coord in self.patch if coord in self.editor.info]
        return {coord: self.editor.info[coord] for coord in coords}

    def _store_inverse(self):

        self.inverse_patch = self.patch.get(self.editor.map)
        self.inverse_info = self._get_inverse_info()

    def _execute(self):

        self.patch.apply(self.editor.map)
        self.patch.apply(self.editor.display)
        for coord in self.inverse_info:
            self.editor.info.pop(coord)

    def undo(self):

        self.inverse_patch.apply(self.editor.map)
        self.inverse_patch.apply(self.editor.display)
        for coord, info_msg in self.inverse_info.items():
            self.editor.info[coord] = info_msg

class BoxCommand(PatchCommand):

    def __init__(self, editor: EditorMode, coord_1: C, coord_2: C, fill: str):

        patch = BoxPatch(coord_1, coord_2,
                         GameMap.solid(fill, editor.x_len, editor.y_len)
                         )

        super().__init__(editor, patch)

class NoiseCommand(PatchCommand): # Implemented

    def __init__(self, editor: EditorMode, template: GameMap):

        patch = OrganicPatch(template)
        super().__init__(editor, patch)

class ReplaceCommand(PatchCommand):

    def __init__(self, editor: EditorMode, old: str, new: str):

        if old == "?":

            old = "!?"

        patch_map = GameMap.solid(Constants.NaC, length=editor.x_len,
                                  width=editor.y_len
                                  )

        for coord in editor.map.find(old, include_character=False):
            patch_map[coord] = PlacementUtils.normalize(new, reverse=True)

        patch = OrganicPatch(patch_map)
        super().__init__(editor, patch)

class FillCommand(PatchCommand):

    def __init__(self, editor: EditorMode, start_coord: C):

        self.editor = editor
        self._patch = GameMap.solid(Constants.NaC, self.editor.x_len, self.editor.y_len)

        self._get_chars(start_coord)
        self._create_patch(start_coord)

        patch = OrganicPatch(self._patch)
        super().__init__(editor, patch)

        del self._patch, self.fill, self.replace

    def _get_chars(self, start_coord):

        self.fill = PlacementUtils.normalize(self.editor.character,
                                             reverse=True
                                             )
        s = self.editor.map[start_coord]
        self.replace = s if s not in MapCharset("?!") else "?!"

    def _create_patch(self, start_coord):

        new_coords = start_coord.adjs("w", "a", "s", "d")

        for c in new_coords:

            if not self.editor.map._bounded(c):
                continue

            if self.editor.map[c] in self.replace and self._patch[c] == Constants.NaC:

                self._patch[c] = self.fill
                self._create_patch(c)

class LineCommand(PatchCommand):

    def __init__(self, editor: EditorMode,
                 coord_1: C, coord_2: C):

        patch_map = GameMap.solid(Constants.NaC, editor.x_len, editor.y_len)
        for coord in C.line(coord_1, coord_2):
            patch_map[coord] = PlacementUtils.normalize(editor.character,
                                                        reverse=True
                                                        )

        patch = OrganicPatch(patch_map)

        super().__init__(editor, patch)

class CircleCommand(PatchCommand):

    def __init__(self, editor: EditorMode,
                 center: C, point_on_circle: C):

        patch_map = GameMap.solid(Constants.NaC, editor.x_len, editor.y_len)
        if not ((center.x == point_on_circle.x) or (
                center.y == point_on_circle.y)):

            raise ValueError(
                "point_on_circle should be vertical/horizontal from the center."
            )

        else:
            radius = int(abs(complex(point_on_circle - center)))

        for coord in C.circle(center, radius):
            patch_map[coord] = PlacementUtils.normalize(editor.character,
                                                        reverse=True
                                                        )

        patch = OrganicPatch(patch_map)

        super().__init__(editor, patch)

class ReflectionCommand(Command):

    def __init__(self, editor: EditorMode, dim: str="x"):

        if dim not in frozenset("xy") or len(dim) != 1:
            raise ValueError("Expected dim to be 'x' or 'y'")

        self.dim = dim

        super().__init__(editor)

    @property
    def flip_func(self):

        x, y = self.editor.x_len, self.editor.y_len

        if self.dim == "x":
            return lambda coord: C(coord.x, y-coord.y-1).as_frozen()
        elif self.dim == "y":
            return lambda coord: C(x-coord.x-1, coord.y).as_frozen()

    def _store_inverse(self):
        pass

    def _execute(self):

        self.editor.pointer_controller.draw(clearing=True)
        self.editor.map = self.editor.map.reflected(dim=self.dim)

        f = self.flip_func

        self.editor.info = InfoMsgs({
            f(coord): info for coord, info in self.editor.info.items()
        })

        self.editor.display = self.editor.display.reflected(dim=self.dim)
        self.editor.pointer_controller.draw()

    def undo(self):

        self._execute()

class DataCommand(Command):

    def __init__(self, editor, attr_name: str, new: str | int | InfoMsgs):

        super().__init__(editor)

        self.attr_name = attr_name
        self.new = new

    @property
    def copy(self):

        if self.attr_name == "info":
            return lambda x: x.copy()
        else:
            return lambda x: x

    def _store_inverse(self):

        self.old = self.copy(getattr(self.editor, self.attr_name))

    def _execute(self):

        setattr(self.editor, self.attr_name, self.new)

    def undo(self):

        setattr(self.editor, self.attr_name, self.old)

class HistoryManager:

    def __init__(self, editor: EditorMode):

        self.editor = editor
        self.history, self.future = deque(), deque()

    @property
    def can_undo(self):
        return bool(self.history)

    @property
    def can_redo(self):
        return bool(self.future)

    def __str__(self):

        n = ' X '
        undo = '<--' if self.can_undo else n
        redo = '-->' if self.can_redo else n

        return f"[{undo}|{redo}]"

    def push(self, *commands: Command): # turn into *commands

        self.history.append(commands)
        self.future.clear()

    def redo(self):

        if not self.can_redo:
            return

        commands = self.future.pop()

        for command in commands:
            command()
        else:
            command.state.apply(self.editor)

        self.history.append(commands)

    def undo(self):

        if not self.can_undo:
            return

        commands = self.history.pop()

        for command in commands[::-1]:
            command.undo()

        if self.history:
            last_command = self.history[-1][0]
            last_command.state.apply(self.editor)
        else:
            EditorContextState.default(self.editor).apply(self.editor)

        self.future.append(commands)

    def clear(self):
        self.history.clear()
        self.future.clear()

    def reset(self):

        self.editor.reset_level_attributes()
        self.clear()

class PointerController:

    POINTER_MOVES = set(["w",
                         "ww", "w'", "'w",
                         "d",
                         "dd", "d'", "'d",
                         "a",
                         "aa", "a'", "'a",
                         "s",
                         "ss", "s'", "'s",

                         "wd", "dw",
                         "wa", "aw",
                         "sd", "ds",
                         "sa", "as"
                         ])

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def draw(self, *, clearing: bool=False, box: bool=False):

        for coord in self.editor.pointer.adjs("w", "a", "s", "d"):

            x1, y1 = coord

            if (x1 in range(self.editor.x_len) and
                    y1 in range(self.editor.y_len)):

                current = self.editor.map[coord]

                if clearing:
                    char = current

                else:
                    char = "."

                if self.editor.display[coord] == "+" and box:
                    continue
                else:
                    self.editor.display[coord] = char

    @staticmethod
    def _get_displacement(player_move: str):

        # Assumes the player_move is a valid move.

        displacement = C(0, 0)

        if "w" in player_move:

            # LMAO. Purpose is to map 1 -> 1, 2 -> 4
            displacement.y += len(player_move) ** 2

        if "s" in player_move:

            displacement.y -= len(player_move) ** 2

        if "d" in player_move:

            displacement.x += len(player_move) ** 2

        if "a" in player_move:

            displacement.x -= len(player_move) ** 2

        return displacement

    def move(self, player_move: str, f: Callable=(lambda x: x)):

        if not player_move:
            return

        self.draw(clearing=True)

        self.editor.pointer += PointerController._get_displacement(player_move)
        self.editor.pointer %= C(self.editor.x_len, self.editor.y_len)
        self.editor.pointer = f(self.editor.pointer)

class BlockPlacementController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def place(self, char: str=None):

        if char is None:
            char = self.editor.character

        p = self.editor.frozen

        # Current selected block from menu

        # Clear
        if char == PlacementUtils.normalize(self.editor.map[p]):

            cmd = CharacterCommand(self.editor, p, " ")
            cmd()
            self.editor.history.push(cmd)

        else: # Place

            # New info block placed! Not verified yet though :/
            char = PlacementUtils.normalize(char, reverse=True)

            cmd = CharacterCommand(self.editor, p, char)
            cmd()
            self.editor.history.push(cmd)

class BoxController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def _draw_box(self, vertex: C, *, clear=False):

        p = self.editor.normal

        def get_char(coord: C):

            x_set, y_set = {p.x, vertex.x}, {p.y, vertex.y}
            if coord.x in x_set and coord.y in y_set:
                return "+"
            elif coord.x in x_set:
                return "|"
            elif coord.y in y_set:
                return "-"
            else:
                return Constants.NaC

        for coord in C.box(vertex, p):
            char = self.editor.map[coord] if clear else get_char(coord)
            self.editor.display[coord] = char

    def _get_box_vertices(self):

        coords = []
        for i in range(1, 3):

            while True:
                self.editor.pointer_controller.draw(box=True)
                clear()

                stdout.write(
                    f"[BOX MODE: ENDPOINT {i}] Define coordinates of box.\n"
                )

                second = i == 2
                if second:
                    self._draw_box(coords[0])

                stdout.write(str(self.editor.display))
                direction: str = IOUtils.input(
                    "Move cursor, press [ENTER] when done: "
                )

                match direction:

                    case "exit" | "quit" | "done":

                        stdout.write("Exiting box mode...\n")

                        for coord in coords:
                            self.editor.display[coord] = self.editor.map[coord]
                        sleep(1)

                        return list()

                    case j if j in PointerController.POINTER_MOVES:

                        if second:
                            self._draw_box(coords[0], clear=True)
                        self.editor.pointer_controller.move(j)

                    case "":
                        p = self.editor.frozen
                        coords.append(p)
                        self.editor.display[p] = "+"
                        break

        return coords

    def draw(self):

        coords = self._get_box_vertices()

        if not coords:
            return

        char = PlacementUtils.normalize(self.editor.character, reverse=True)
        cmd = BoxCommand(self.editor, *coords, char)
        cmd()
        self.editor.history.push(cmd)

class NoiseController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def _draw_noise(self, y: int, stretch: int | float=1):

        template = GameMap.solid(Constants.NaC,
                                 length=self.editor.x_len, width=self.editor.y_len)

        char = PlacementUtils.normalize(self.editor.character, reverse=True)

        noise = PerlinNoise()

        # Get noise values and draw them
        for x in range(self.editor.x_len):

            noise_val = noise.noise(x + random(), y + random())

            # stretch acts as a multiplier on noise_val
            relative_val = y + (noise_val * stretch)

            height = min(Constants.Y_LEN, round(relative_val))

            for new_y in range(height, -1, -1):
                template[C(x, new_y)] = char

        return template

    def _get_y(self):

        default_display = self.editor.display.copy()
        self.editor.pointer_controller.draw(clearing=True)

        while True:

            clear()

            self.editor.display = default_display.copy()
            self.editor.display[self.editor.pointer.y] = "-"

            self.editor.pointer_controller.draw()

            stdout.write("[NOISE MODE: HEIGHT] Define surface of terrain.\n")
            stdout.write(str(self.editor.display))
            action = IOUtils.input("Move cursor, press [ENTER] when done: ")

            if not action:
                self.editor.display = default_display.copy()
                return self.editor.pointer.y

            self.editor.pointer_controller.move(action)

    def _get_stretch(self, y: int):

        default_pointer = self.editor.pointer.copy()
        default_display = self.editor.display.copy()

        while True:

            clear()

            self.editor.display = default_display.copy()

            self.editor.display[y] = "-"
            for i in range(default_pointer.y + 1, self.editor.pointer.y + 1):
                self.editor.display[C(self.editor.pointer.x, i)] = "|"
            self.editor.display[self.editor.pointer] = "+"

            self.editor.pointer_controller.draw()

            stdout.write("[NOISE MODE: HEIGHT] Define stretch for noise.\n")
            stdout.write(str(self.editor.display))
            action = IOUtils.input("Move cursor, press [ENTER] when done: ")

            if not action:
                self.editor.display = default_display.copy()
                return (self.editor.pointer - default_pointer).y

            self.editor.pointer_controller.move(action,
                                                f=lambda c: C(c.x, max(c.y, y)))

    def noise(self):

        self.editor.pointer_controller.draw(clearing=True)

        y = self._get_y()
        stretch = self._get_stretch(y)

        template = self._draw_noise(y, stretch)

        cmd = NoiseCommand(self.editor, template)
        cmd()

        self.editor.history.push(cmd)
        self.editor.pointer_controller.draw()

class LineController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def _get_endpoints(self):

        endpoints = []

        for i in range(1, 3):

            while True:

                self.editor.pointer_controller.draw(box=True)

                d = self.editor.display.copy()

                if i == 2:
                    for coord in C.line(endpoints[0], self.editor.pointer):
                        d[coord] = "-"

                for endpoint in *endpoints, self.editor.pointer:
                    d[endpoint] = "+"

                clear()

                stdout.write(
                    f"[LINE MODE: ENDPOINT {i}] Define line endpoints.\n"
                )

                stdout.write(str(d))
                direction: str = IOUtils.input(
                    "Move cursor, press [ENTER] when done: "
                )

                match direction:

                    case "exit" | "quit" | "done":

                        stdout.write("Exiting line mode...\n")

                        sleep(1)

                        return list()

                    case j if j in PointerController.POINTER_MOVES:

                        self.editor.pointer_controller.move(j)

                    case "":
                        p = self.editor.frozen
                        endpoints.append(p)
                        self.editor.display[p] = "+"
                        break

        return endpoints

    def draw(self):

        endpoints = self._get_endpoints()
        if not endpoints:
            return
        else:
            cmd = LineCommand(self.editor, *endpoints)
            cmd()
            self.editor.history.push(cmd)

class CircleController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def _get_center(self) -> C:

        while True:

            clear()
            stdout.write("[CIRCLE MODE: CENTER] Find center of circle.\n")

            self.editor.pointer_controller.draw()
            stdout.write(str(self.editor.display))

            direction = IOUtils.input("Move cursor, press [ENTER] when done: ")

            match direction:

                case "exit" | "quit" | "done":

                    stdout.write("Exiting circle mode...\n")

                    sleep(1)

                    return None

                case j if j in PointerController.POINTER_MOVES:

                    self.editor.pointer_controller.move(j)

                case "":
                    return self.editor.normal

    def _get_point_on_circle(self, center):

        self.editor.pointer_controller.draw(clearing=True)
        default = self.editor.display.copy()

        while True:

            clear()
            self.editor.display = default.copy()
            self.editor.display[center.y] = "-"

            r = int(abs(complex(self.editor.pointer - center)))
            for p in C.circle(center, r):
                self.editor.display[p] = "'"

            self.editor.display[center] = "+"
            self.editor.display[self.editor.pointer] = "+"

            self.editor.pointer_controller.draw()

            stdout.write("[CIRCLE MODE: RADIUS] Define radius.\n")

            stdout.write(str(self.editor.display))

            direction = IOUtils.input("Move using [a/d], press [ENTER] when done: ")

            match direction:

                case "exit" | "quit" | "done":

                    stdout.write("Exiting circle mode...\n")

                    sleep(1)

                    return None

                case j if j in {"a", "aa", "a'", "'a",
                                "d", "dd", "d'", "'d"}:

                    self.editor.pointer_controller.move(j)

                case "":
                    self.editor.display = default.copy()
                    return self.editor.normal

    def draw(self):

        center = self._get_center()

        if center is None:
            return

        point_on_circle = self._get_point_on_circle(center)

        if point_on_circle is None:
            return

        cmd = CircleCommand(self.editor, center, point_on_circle)
        cmd()
        self.editor.history.push(cmd)

class _InfoController:

    def __init__(self, editor: EditorMode):
        self.editor = editor

    def _info_drop_down(self, info: str):

        info = f"Current info message: {info if info else '-'}"

        L = self.editor.x_len

        drop_down = []
        drop_down.append(f"| {shorten(info, width=L-2):<{L-2}} |")
        drop_down.append("~"*(L+2))

        return "\n".join(drop_down)

    def _select_info(self):

        self.editor.pointer_controller.draw(clearing=True)

        # Get all info indices, whether they have been written
        indices = sorted(self.editor.map.find("?!", include_character=False),
                         key=lambda coord: (-coord.y, coord.x))

        num_indices = len(indices)

        if not indices:
            return

        original_pointer = self.editor.normal

        # Find starting index with least distance (use complex modulus)
        c = complex(original_pointer)
        current_ind = min(
            range(num_indices), key=lambda i: abs(complex(indices[i])-c)
        )

        while True:

            self.editor.pointer = indices[current_ind].as_normal()
            self.editor.pointer_controller.draw()

            info = self.editor.info[self.editor.normal]

            clear()

            drop = self._info_drop_down(info)

            s = \
                "Scroll through info blocks using [a/d], press [Enter] when done."

            stdout.write(
                f"{s}\n{self.editor.display}{drop}\n"
            )

            user_input = IOUtils.input("Select info: ", sanitize=True)
            n = len(user_input)

            match user_input.lower():

                case "s" | "ss" | "d" | "dd":
                    current_ind += n
                case "w" | "ww" | "a" | "aa":
                    current_ind -= n
                case "":
                    return info

                case "exit":
                    return

            current_ind %= num_indices
            self.editor.pointer_controller.draw(clearing=True)

    def edit(self):

        current_info = self._select_info()

        if current_info is None:
            return

        new_info = self.editor.info.copy()

        clear()

        i = current_info if current_info else "-"

        stdout.write(
            f"Type a message.\n{self.editor.display}Current message: {i}\n"
        )

        while True:
            info = IOUtils.input("-> ")

            if len(info) <= LevelData.MAX_INFO_WIDTH:

                # Will clear info
                cmd1 = CharacterCommand(self.editor, self.editor.normal, "?")
                cmd1()

                # Put the new info in place.
                new_info[self.editor.normal] = info
                new = new_info.copy()
                cmd2 = DataCommand(self.editor, "info", new)
                cmd2()

                break

            else:
                stdout.write(
                    "Try again! Your info message is over 200 characters.\n"
                )

        self.editor.history.push(cmd1, cmd2)

class _TimeLimitController:

    def __init__(self, editor: EditorMode):
        self.editor = editor

    def _clear_time(self):

        cmd = DataCommand(self.editor, "time", float("inf"))
        cmd()
        self.editor.history.push(cmd)

    def _edit_time(self):

        while True:

            time_str = (
                "-" if self.editor.time == float("inf") else self.editor.time
            )
            d = str(self.editor.display)

            clear()
            stdout.write(
                f"Create a time limit.\n{d}Current time limit: {time_str} seconds\n"
            )

            player_input = IOUtils.input("-> ")

            if (not (player_input.strip()).isdecimal()
                    or not player_input.strip()):

                stdout.write("Try again! Conversion failed.\n")
                continue

            new_time = int(player_input)

            if new_time > LevelData.MAX_TIME:
                stdout.write(f"Try again! {new_time} is over 1,000 seconds.\n")
                continue

            cmd = DataCommand(self.editor, "time", new_time)
            cmd()
            self.editor.history.push(cmd)

            break

    def edit_time(self):

        str_list = [
            "Clear Time Limit",
            "Set New Time Limit",
            "Exit"
        ]
        while True:

            clear()
            stdout.write(StringUtils.menu("Edit Time Limit", str_list))

            selection = IOUtils.input(sanitize=True)

            match selection:

                case "1":
                    self._clear_time()
                case "2":
                    self._edit_time()
                case "x":
                    break
                case _:
                    continue

            break

class DataController:

    def __init__(self, editor: EditorMode):

        self.editor = editor
        self.info_controller = _InfoController(editor)
        self.time_limit_controller = _TimeLimitController(editor)

    def _edit_title(self):

        title_str = "-" if not self.editor.title else self.editor.title
        d = str(self.editor.display)

        clear()
        stdout.write(
            f"Create a title for your level.\n{d}Current title: {title_str}\n"
        )

        while True:
            title = IOUtils.input("-> ")

            if len(title) <= LevelData.MAX_TITLE_WIDTH and title.strip():

                cmd = DataCommand(self.editor, "title", title)
                cmd()
                self.editor.history.push(cmd)
                return

            elif not title.strip():
                stdout.write("Try again! You can't have all whitespace.\n")
            else:
                stdout.write("Try again! Your title is over 100 characters.\n")

    def _edit_desc(self):

        desc_str = "-" if not self.editor.desc else self.editor.desc
        d = str(self.editor.display)

        clear()
        stdout.write(
            f"Create a description for your level.\n{d}Current description: {desc_str}\n")

        while True:
            desc = IOUtils.input("-> ")

            if len(desc) <= LevelData.MAX_DESC_WIDTH:

                cmd = DataCommand(self.editor, "desc", desc)
                cmd()
                self.editor.history.push(cmd)
                return

            else:
                stdout.write(
                    "Try again! Your description is over 300 characters.\n")

    def _edit_time(self):

        self.time_limit_controller.edit_time()

    def _edit_info(self):

        self.info_controller.edit()

    def edit(self):

        english = [
            "Edit Title",
            "Edit Description",
            "Edit Time Limit",
            "Edit Info"
        ]
        attr_names = [
            "title",
            "desc",
            "time",
            "info"
        ]

        menu = StringUtils.menu("Editing Data", english + ["Exit"])

        while True:

            clear()

            stdout.write(menu)
            selection = IOUtils.input(sanitize=True)

            match selection:

                case "1" | "2" | "3" | "4":
                    field = attr_names[int(selection)-1]
                    getattr(self, f"_edit_{field}")()
                    break

                case "x":
                    break
                case _:
                    continue

class EyedropperController:

    def __init__(self, editor):

        self.editor = editor

    def get_block(self):

        current = self.editor.map[self.editor.pointer]

        if current in self.editor.block_cursor:
            self.editor.block_cursor.goto(current)

class ReplaceController:

    def __init__(self, editor):

        self.editor = editor

    def get_char(self, name: str):

        self.editor.clear = False

        result = ""

        self.editor.pointer_controller.draw(clearing=True)

        while True:

            menu = self.editor.block_cursor.block_menu(
                width=self.editor.map.x_len
            )

            d = str(self.editor.display)

            clear()

            stdout.write(
                f"{name.upper()}: Pick a character.\n{d}{menu}\n-> ")

            player_input = IOUtils.input()

            match player_input:
                case ";" | ";;" | "'" | "''":
                    self.editor.block_cursor.shift_char(player_input)

                case i if i in {"[", "[[", "]", "]]"}:
                    self.editor.block_cursor.shift_mode(player_input)

                case "exit" | "quit":
                    break

                case "":
                    result = self.editor.character
                    break

        self.editor.pointer_controller.draw()
        return result

    def replace(self):

        old = self.get_char("Previous")

        if not old:
            return

        new = self.get_char("New")

        if not new:
            return

        cmd = ReplaceCommand(self.editor, old, new)
        cmd()
        self.editor.history.push(cmd)

class ReflectionController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    @staticmethod
    def get_centers(length: int):

        center = length / 2

        if center.is_integer():
            return [int(center) - 1, int(center)]
        else:
            return [int(center)]


    def get_maps(self):

        x_map, y_map = self.editor.display.copy(), self.editor.display.copy()

        x_centers, y_centers = (
            ReflectionController.get_centers(self.editor.x_len),
            ReflectionController.get_centers(self.editor.y_len)
        )

        for y in range(self.editor.y_len):
            if len(x_centers) == 1:
                y_map[C(x_centers[0], y)] = "|"
            else:
                y_map[C(x_centers[1], y)] = "|"

        if len(y_centers) == 1:
            x_map[y_centers[0]] = "-"
        else:
            x_map[y_centers[1]] = "_"

        return x_map, y_map

    def get_axis(self):

        self.editor.pointer_controller.draw(clearing=True)

        # x_map is reflecting over x-axis
        # y_map is reflecting over y-axis

        maps, dims = self.get_maps(), "XY"
        pointer = 0

        while True:

            clear()

            dim, d = dims[pointer], maps[pointer]

            stdout.write(
                f"{dim}-AXIS: Pick an axis to reflect over by hitting [ENTER], "
                f"[d] when done.\n{d}-> "
            )

            player_input = IOUtils.input()

            match player_input:

                case "":
                    pointer = 1 - pointer
                case "d":
                    return dim.lower()
                case "x":
                    return

    def reflect(self):

        axis = self.get_axis()

        if axis is None:
            return

        cmd = ReflectionCommand(self.editor, axis)
        cmd()
        self.editor.history.push(cmd)

class FillController:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def fill(self):

        cmd = FillCommand(self.editor, self.editor.pointer)
        cmd()
        self.editor.history.push(cmd)

class Renderer:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def render(self):

        t = shorten(self.editor.title, placeholder="...", width=30)
        c = '[CLEAR MODE]' if self.editor.clear else ''
        u = str(self.editor.history)

        self.editor.pointer_controller.draw()

        stdout.write(f"[Editing '{t}'] {u} {c}\n")

        stdout.write(str(self.editor.display))

        stdout.write(
            self.editor.tool_cursor.tool_menu(
                width=self.editor.map.x_len) + "\n")
        stdout.write(
            self.editor.block_cursor.block_menu(
                width=self.editor.map.x_len) + "\n")

        # Game map box.
        if self.editor.debug:
            stdout.write("Game map:\n")
            stdout.write(str(self.editor.map))

class Saver:

    def __init__(self, editor: EditorMode):

        self.editor = editor

    def save(self) -> LevelData | None:

        if self.editor.override:
            result = self.editor.final_data
            return LevelData.from_tuple(result)

        start_num = self.editor.map.count("S")

        # Conditions for saving a map.
        if "F" not in self.editor.map:
            stdout.write("Try again! You need a finish block ('F').\n")
        elif not start_num:
            stdout.write("Try again! You need a start block ('S').\n")
        elif start_num > 1:
            stdout.write("Try again! You can only have 1 start block ('S').\n")
        elif "!" in self.editor.map:
            stdout.write("Try again! You have unwritten info blocks ('!').\n")
        else:

            result = self.editor.final_data
            return LevelData.from_tuple(result)

        IOUtils.input("Press [ENTER] to continue. ")

class EditorMode:

    def __init__(self,
                 level: LevelData=None,
                 debug: bool=False,
                 override: bool=False,
                 hotkeys: Hotkeys=None
                 ):

        if level is None:
            level = LevelData()

        self.debug = debug
        self.override = override

        self.hotkeys = Hotkeys() if hotkeys is None else hotkeys

        self._level_data = level.copy()

        self.reset_level_attributes()
        self.setup_editor_config()

    def reset_level_attributes(self):

        self.map = self._level_data.map.copy()
        self.desc = self._level_data.desc
        self.time = self._level_data.time
        self.title = self._level_data.title
        self.info = InfoMsgs.from_memory_efficient(
            self._level_data.info, self.map
        )
        self.points = self._level_data.points
        self.author = self._level_data.author

        self.display = self._level_data.map.copy()
        self.pointer = self.default_pointer

    @property
    def default_pointer(self):

        return C(
            self.x_len // 2,
            self.y_len // 2
        )

    @property
    def normal(self):

        return self.pointer.as_normal().copy()

    @property
    def frozen(self):

        return self.pointer.as_frozen().copy()

    @property
    def x_len(self):
        return self.map.x_len

    @property
    def y_len(self):
        return self.map.y_len

    def setup_editor_config(self):

        self.pointer_controller = PointerController(self)
        self.block_placer = BlockPlacementController(self)
        self.box_drawer = BoxController(self)
        self.noise_gen = NoiseController(self)
        self.data_controller = DataController(self)
        self.history = HistoryManager(self)
        self.renderer = Renderer(self)
        self.saver = Saver(self)
        self.eyedropper = EyedropperController(self)
        self.replacer = ReplaceController(self)
        self.reflector = ReflectionController(self)
        self.filler = FillController(self)
        self.line_drawer = LineController(self)
        self.circle_drawer = CircleController(self)

        self.block_cursor = BlockCursorLoc()
        self.tool_cursor = ToolCursorLoc()

        self.clear = False

    @property
    def character(self):
        return " " if self.clear else str(self.block_cursor)

    @property
    def final_data(self):

        return LevelData(
            title=self.title,
            author=self.author,
            date=self._level_data.date,
            desc=self.desc,
            map=GameMap(self.map),
            time=self.time,
            info=MemoryEfficientInfoMsgs(self.info),
            points=self.points
        )

    def edit(self):

        while True:

            clear()
            self.renderer.render()

            user_input = IOUtils.input("Move cursor: ", sanitize=True)

            match user_input:

                case "save" | "done":
                    lvl = self.saver.save()
                    if lvl is not None:
                        return lvl
                case "exit" | "quit":
                    stdout.write("Exiting...\n")
                    sleep(0.75)
                    return LevelData.NULL

                case m if m in PointerController.POINTER_MOVES:
                    self.pointer_controller.move(m)

                case "e" | "eyedropper":
                    self.eyedropper.get_block()
                case "c" | "clear":
                    self.clear = not self.clear
                case "q" | "execute":
                    self.tool_cursor.execute(self)

                case "reset" | "r":
                    self.history.reset()
                case "undo" | "z":
                    self.history.undo()
                case "redo" | "y":
                    self.history.redo()

                case ";" | ";;" | "'" | "''":
                    self.block_cursor.shift_char(user_input)
                case "[" | "[[" | "]" | "]]":
                    self.block_cursor.shift_mode(user_input)
                case "-" | "--" | "=" | "==":
                    self.tool_cursor.shift_tool(user_input)

                case "f" | "data":
                    self.data_controller.edit()

                case "h":

                    self.hotkeys.view()

                case i if i in self.hotkeys:

                    self.block_placer.place(char=self.hotkeys[i])

                case "":

                    self.block_placer.place()
