from __future__ import annotations

from typing import Literal, Optional
from collections.abc import Iterable
from clear import clear
from time import perf_counter, sleep
from enum import Flag, Enum, auto
from random import sample, random
from functools import partial, wraps
from itertools import cycle
from utils import PerlinNoise, IOUtils
from sys import stdout
from maps import (GameMap, MultiMap, LevelData, C, FrozenC, Coordinates,
                  InfoMsgs, MemoryEfficientInfoMsgs, Constants, MapCharset)
from textwrap import shorten, wrap
from dataclasses import dataclass, astuple
# import logging # `Log

"""<plat.py> Reference:

- class Result(Flag): An enum that defines 4 different flags.
NONE - Died, exited, etc.
WON - player won the game
COIN - player got the coin
TIME - player beat the level before the time limit.

- class Platformer: A class that has one public method .play().
This can be used to run the game. It will terminate once the 
player wins or loses, and returns a Result Flag.

- class Tower(Platformer): A class that inherits from Platformer,
but introduces a scrolling mechanism to play taller levels easily.
This is used for the final Tower level. It also can be played
with .play().

- class Endless(Platformer): A class that takes in some metrics
to randomly generate a level using Perlin Noise. It also
contains a DFS-like algorithm for checking if a level is possible
to beat. (Does not work with more complex features like
platforms, as the checks do not update the game state.)
"""

# logger = logging.getLogger("debug_logger") # `Log
# logging.basicConfig(filename="debug.log", encoding="utf-8", level=logging.DEBUG, filemode="w") # noqa `Log

# Global character sets

CHARS = MapCharset("#*LlAnNX<>V^_KkHhx@SF:-|'\"?/\\`()[]{}+=$;.,123456789")

HARD = MapCharset("#*LlAnNX<>V^123456789")
NOT_PASSABLE = MapCharset("#*LlAnNX<>V^123456789_")
INTERRUPT = MapCharset("x_")
TRANSPARENT = MapCharset(" :'\"Kk?`()[]{}/\\+=$@SF;.,")

LOCKS = MapCharset("lLAnNX")
KEYS = MapCharset("KkHh")
COLLECTIBLES = MapCharset("Kk@")
COUNTDOWN = MapCharset("123456789")
ARROWS = MapCharset("<>^V")
HORIZONTAL = MapCharset("-<>")
VERTICAL = MapCharset("|^V")
GRAVITY = MapCharset("+=")
STOP = MapCharset("+=")
TELEPORT = MapCharset("()[]{}")
PLACEABLE = CHARS - MapCharset("`")

SLOW_X, FAST_X = 1, 4
Y = 2

class Result(Flag):

    """An enum that defines 4 different flags.

    NONE - died, exited, etc.
    WON - player won the game
    COIN - player got the coin
    TIME - player beat the level before the time limit

    These are used to pass values out of the Platformer mode when a player
    wins / dies / exits.
    """

    NONE = 0
    WON = auto()
    COIN = auto()
    TIME = auto()

    def __str__(self):

        if self == (Result.WON | Result.COIN | Result.TIME):
            return "Coin + Time"
        elif self == (Result.WON | Result.COIN):
            return "Coin"
        elif self == (Result.WON | Result.TIME):
            return "Time"
        elif self == Result.WON:
            return "Won"
        elif self == Result.NONE:
            return "-"

    @property
    def order(self):

        """Returns the 'order' of a Result - how many things
        were achieved in a run-through. This is the multiplier
        applied to the base score of a level."""

        if self == (Result.WON | Result.COIN | Result.TIME):
            return 3
        elif self == (Result.WON | Result.COIN):
            return 2
        elif self == (Result.WON | Result.TIME):
            return 2
        elif self == Result.WON:
            return 1
        elif self == Result.NONE:
            return 0

@dataclass(frozen=True, slots=True)
class Status:

    """The data type that is sent out of the Platformer
    class, containing the player result as well as the
    time the user took to complete the level."""

    result: Optional[Result] = None
    time: Optional[int | float] = None

    def __iter__(self):

        return iter(astuple(self))

    def __repr__(self):

        return f"Status(result={self.result!s}, time={self.time:3f})"

    def __bool__(self):

        return self.result is not None and self.time is not None

    @classmethod
    def from_plat(cls, platformer: Platformer, result: Result):

        """Takes in a platformer object and a result to create
        a Status object."""

        return cls(result, platformer.elapsed)

class AliveCode(Enum):

    """An enum that tracks the state of the player in-game
    frame by frame. This is different from the Result flag
    that returns the end state of the player."""

    DEAD = 0
    ALIVE = 1
    WON = 2

    def is_alive(self):

        """Returns whether the player is alive
        (self == AliveCode.ALIVE). Is false
        when the player has won or died."""

        return self.value == 1

    def is_won(self):

        """Returns whether the player has won
        (self == AliveCode.WON). Is false
        when the player is alive or dead."""

        return self.value == 2

class Asterisks(set):

    """A set object used in the Platformer class, which tracks
    the coordinates of the asterisks that have been stepped on.
    Every tick, the set is populated. The asterisks are then
    deleted from the game map, and the set is cleared. Also
    referred to as the 'stepped on' set in the code."""

    def __repr__(self):

        return f"Asterisks({', '.join(str(i) for i in self)})"

    def __contains__(self, coord: Coordinates) -> bool:

        """Allows for checking membership using normal coordinates."""

        if not isinstance(coord, Coordinates):
            raise ValueError(f"{coord} is not a coordinate.")

        coord = coord.as_frozen()

        return super().__contains__(coord)

    def add(self, coord: Coordinates) -> None:

        """Allows for adding normal coordinates."""

        if not isinstance(coord, Coordinates):
            raise ValueError(f"{coord} is not a coordinate.")

        coord = coord.as_frozen()

        super().add(coord)

    def populate(self, platformer: Platformer, frame: ExecutionFrame):

        """Uses a Platformer object as well as the current coordinates of the
        player to determine if the player is currently above an asterisk
        block. If so, the coordinate is added to the set to be deleted."""

        below = frame.coords.adj("s", platformer.gravity).as_frozen()

        if platformer.maps.game[below] == "*":
            self.add(below)

@dataclass(slots=True)
class Keys:

    """Tracks whether the lowercase and uppercase keys have
    been collected."""

    k: bool = False
    K: bool = False

    def get_char(self, char: Literal["k", "K"]):

        return getattr(self, char)

    def set_char(self, char: Literal["k", "K"], collected: bool):

        setattr(self, char, collected)

    def __iter__(self):

        return iter((self.k, self.K))

@dataclass(slots=True)
class ExecutionFrame:

    """A class that tracks the state of the player, including
    their coordinates and whether they are alive.
    ExecutionFrame objects get passed through the movement
    algorithms in the Platformer class.
    The ExecutionFrame object has two methods: freeze
    and normalize, which convert the Coordinate objects
    into FrozenC and C respectively."""

    alive: AliveCode
    coords: Coordinates
    apply_grav: bool = True

    def freeze(self):
        self.coords = self.coords.as_frozen()

@dataclass(slots=True)
    def normalize(self):
        self.coords = self.coords.as_normal()

class CoinCounter:

    total: int
    collected: int = 0

    def __str__(self):

        return f"{self.collected}/{self.total}"

    def update(self):
        self.collected += 1

    @property
    def full(self):
        return self.collected == self.total

    def __bool__(self):
        return bool(self.total)

@dataclass(frozen=True, slots=True)
class Cell:

    coord: FrozenC
    char: str

    def __iter__(self):
        return iter((self.coord, self.char))

class Cells:

    def __init__(self, cells: Iterable[Cell]=()):

        self.cells = set(cells)

    def add(self, cell: Cell):

        self.cells.add(cell)

    def __iter__(self):
        return iter(self.cells)

    @classmethod
    def from_map(cls, game_map: GameMap, charset: MapCharset):
        return Cells({Cell(*i) for i in game_map.find(charset)})

class PlatformGenerator:

    __slots__ = ("game_map", "last_value", "default")

    def __init__(self, game_map: GameMap=None, initial_coords: Coords=None):

        if (game_map is None) + (initial_coords is None) == 1:
            raise TypeError(
                "PlatformGenerator takes 0 or 2 arguments, 1 was given")

        self.game_map = game_map
        self.last_value = set() if initial_coords is None else initial_coords
        self.default = game_map is None and initial_coords is None

    def __next__(self) -> Coords:

        result = set()

        if self.default:
            return result

        for coord, direction in self.last_value:
            x, y = coord
            new_dir = direction

            # Very long block that updates x/y and direction for turns.

            if direction == ">":
                if self.game_map[C(x+1, y)] in HORIZONTAL:
                    x += 1
                else:
                    x -= 1
                    new_dir = "<"
            elif direction == "<":
                if self.game_map[C(x-1, y)] in HORIZONTAL:
                    x -= 1
                else:
                    x += 1
                    new_dir = ">"
            elif direction == "V":
                if self.game_map[C(x, y-1)] in VERTICAL:
                    y -= 1
                else:
                    y += 1
                    new_dir = "^"
            elif direction == "^":
                if self.game_map[C(x, y+1)] in VERTICAL:
                    y += 1
                else:
                    y -= 1
                    new_dir = "V"

            result.add((FrozenC(x, y), new_dir))

        self.last_value = result

        return result

    def __iter__(self):
        return self

class CountdownGenerator:

    __slots__ = ("iterators", "default", "last_value")

    def __init__(self, initial=None):

        self.iterators = dict()
        self.default = initial is None

        if not self.default:
            for coord, char in initial:

                r = range(int(char), -1, -1)
                iterator = cycle(r)
                next(iterator)

                self.iterators[coord] = iterator

        self.last_value = initial

    def __next__(self):

        result = set()

        if self.default:
            return result

        for coord, obj in self.iterators.items():

            num = next(obj)
            char = str(num) if num else "`"

            result.add((coord, char))

        self.last_value = result

        return result

    def __iter__(self):

        return self

class Portals:

    """A class containing the coordinates of linked-up
    teleportation portals."""

    __slots__ = ("pairs",)

    def __init__(self, game_map: GameMap) -> None:

        pairs = dict()

        # Lists of coordinates of occurrences.
        for char1, char2 in zip("[({", "])}"):

            coords = frozenset(game_map.find(char1))
            pair_coords = frozenset(game_map.find(char2))

            if coords and pair_coords: # (At least) 1 to 1.
                pairs[coords] = pair_coords
                pairs[pair_coords] = coords

        self.pairs = pairs

    def __getitem__(self, coords: Coordinates) -> list[FrozenC]:

        """From the coordinate of a portal, retrieves the coordinates
        of all other portals that link to it. If the coordinate
        is not of a portal, then a KeyError is raised."""

        for coord_set in self.pairs:

            if coords.as_frozen() in coord_set:
                return list(self.pairs[coord_set])

        else:
            raise KeyError(f"{coords!r} not found.")

class Locks:

    """A class that acts as a lock manager,
    tracking which coordinates should be opened
    and which should not be."""

    __slots__ = ("locks", "open_locks")

    def __init__(self, default_map: GameMap):

        # All locks
        self.locks = {i: default_map.find(i) for i in LOCKS}

        # Locks that are currently opened.
        self.open_locks = set()

    def __getitem__(self, lock_char: str) -> set[FrozenC]:

        return self.locks[lock_char]

    def is_open(self, lock_char: str) -> bool:

        return lock_char in self.open_locks

    def edit(self, lock_char: str, open: bool):

        """Subroutine for replacing locks, based on:
        - open: Boolean condition for the lock to be opened.
        - lock_char: Character representation of the lock to be edited.
        """

        if open:
            self.open_locks.add(lock_char)
        else:
            self.open_locks.discard(lock_char)

@dataclass(slots=True)
class MovementParameters:

    FAST_X: int = FAST_X
    Y: int = Y

    def reset(self):
        self.FAST_X = FAST_X
        self.Y = Y

class PlatformerMap:

    __slots__ = ("both", "countdown_gen", "platform_gen")

    def __init__(self, game_map: GameMap):

        self.both = MultiMap(game_map.copy(), game_map.copy())

        self.countdown_gen = CountdownGenerator(game_map.find(COUNTDOWN))
        self.platform_gen = PlatformGenerator(game_map, game_map.find(ARROWS))

    @property
    def game(self):

        return self.both.game_map

    @property
    def default(self):

        return self.both.default_map

    def update_countdown_blocks(self):

        blocks = next(self.countdown_gen)

        for coord, char in blocks:

            self.game[coord] = char
            self.default[coord] = char

    def update_platforms(self) -> None:

        """Use new coordinates obtained by the generator function to
        update moving platforms for the next tick."""

        arrow_coords = self.platform_gen.last_value

        new_platform_coords = next(self.platform_gen)

        # Clear previous arrows.
        for coord, char in arrow_coords:

            track_char = "-" if char in MapCharset("<>") else "|"
            self.both[coord] = track_char

        # Render new arrows.
        for coord, char in new_platform_coords:
            self.both[coord] = char

    def clear_asterisks(self, stepped_on: Asterisks):

        """Clears the stepped on set."""

        for coord in stepped_on:
            self.clear_coord(coord)

    def clear_coord(self, coord: Coordinates):

        self.both[coord] = " "

@dataclass(frozen=True)
class WinCondition:

    win_repr: str
    status: Status
    jumps: int

class WinDeathChecker:

    __slots__ = ("p",)

    def __init__(self, platformer: Platformer):

        self.p = platformer

    def add_to_stub(self, res: Result, stub: str):

        if self.p.coin_counter.total == 1:
            coin_str = f" Coin [{'+' if Result.COIN in res else 'x'}]"
        elif not self.p.coin_counter:
            coin_str = ""
        else:
            coin_str = f" Coins [{self.p.coin_counter!s}]"

        stub += coin_str

        if self.p.timelimit != float("inf") and not self.p.time_surpassed:

            res |= Result.TIME

            time_str = " Time [+]"

        elif self.p.timelimit != float("inf"):

            time_str = " Time [x]"
        else:
            time_str = ""

        stub += time_str
        stub += f" [{self.p.elapsed:.2f}]"

        return WinCondition(stub, Status.from_plat(self.p, res), self.p.jumps)

    def loss(self, stub):

        if self.p.coin_counter.total == 1:
            coin_str = " Coin [x]"
        elif not self.p.coin_counter:
            coin_str = ""
        else:
            coin_str = " Coins [x]"

        stub += coin_str

        time_str = "" if self.p.timelimit == float("inf") else " Time [x]"

        return WinCondition(stub + f"{time_str} [You died!] ",
                            *self.p.death_status)

    def get_return_value(self):

        """A huge comparison block that checks whether the
        player won or lost. It then prints the appropriate
        string and returns the result."""

        stub = "Won [+]"

        # Coins were collected.
        if (self.p.frame.alive.is_won() and self.p.coin_counter and
                self.p.coin_counter.full):

            res = Result.WON | Result.COIN

            return self.add_to_stub(res, stub)

        # Coin was not collected, but still alive.
        elif self.p.frame.alive.is_won():

            res = Result.WON
            return self.add_to_stub(res, stub)

        elif self.p.frame.alive == AliveCode.DEAD:

            return self.loss("Won [x]")

class Renderer:

    __slots__ = (
        "text_length",
        "platformer",
        "checker",
        "_tower",
        "display_desc",
        "display_coords")

    def __init__(self, platformer: Platformer,
                 display_desc=True, display_coords=False
                 ):

        self.text_length = platformer._level_data.text_length(display_desc)
        self.display_desc = display_desc
        self.display_coords = display_coords
        self.platformer = platformer
        self.checker = WinDeathChecker(platformer)
        self._tower = isinstance(platformer, Tower)

    def _fill(self, string: str) -> str:

        string = wrap(string.replace("\n", ""),
                      width=self.platformer.maps.game.x_len+2)

        difference = self.text_length - len(string)
        return "\n".join(string) + ("\n" * difference)

    def _format_time(self):

        elapsed, timelimit = self.platformer.elapsed, self.platformer.timelimit

        # Exclamation marks.
        exc = (" (!) " if elapsed > timelimit else " ")

        if self.platformer.timelimit != float("inf"):
            return f"Time: <{elapsed:.2f}|{timelimit:.2f}>{exc}"
        else:
            return ""

    def _update_camera(self, y: int) -> None:

        """Finds the new top and bottom y-coordinates for the screen,
        positioning the player in the middle of the screen if it can.
        If the bottom, which is 6 below the y coordinate, is less than
        0, it will default to 0. Similarly, if 6 above y is
        above the map, it will default to the map maximum."""

        self.platformer.bottom = max(0, y - (self.platformer.screen_len // 2))

        self.platformer.top = min(self.platformer.maps.game.y_len - 1,
                                  self.platformer.bottom + self.platformer.screen_len)

        if self.platformer.top == self.platformer.maps.game.y_len - 1:
            self.platformer.bottom = \
                (self.platformer.top - self.platformer.screen_len)

    def print_desc(self):

        x_len = self.platformer.maps.game.x_len

        if self._tower:
            y_len = self.platformer.screen_len
        else:
            y_len = self.platformer.maps.game.y_len

        full_y_len = (y_len + 2) + self.text_length
        if self.platformer.timelimit != float("inf"):
            full_y_len += 1

        desc = (
            f"[{self.platformer.title.upper()}] Description: {self.platformer.desc}"
        ) if self.platformer.desc else ""

        lines = wrap(
            desc, width=x_len-2)

        lines = [f"| {line:<{x_len-2}} |" for line in lines]

        display = ["~"*(x_len+2)]
        display.extend(lines)

        r = 2 if self.platformer.meta else 0
        remainder = (full_y_len - r) - len(display) - 1
        display.extend([f"| {' '*(x_len-2)} |" for i in range(remainder)])

        if self.platformer.meta:
            author = f"[Created by: {self.platformer.author}]"
            date = f"[Date of creation: {self.platformer.date}]"
            display.append(f"| {author:<{x_len-2}} |")
            display.append(f"| {date:<{x_len-2}} |")

        display.append("~" * (x_len+2))

        stdout.write("\n".join(display) + "\n")

    def _prefix(self, string: str, prefix: str):

        if len(prefix) != 1:
            raise ValueError("Expected string of length 1")

        return f"{prefix} | {string}"

    def _render(self, game_map: GameMap=None, string: str=""):

        """Prints the map and all the other information."""

        x_len = self.platformer.maps.game.x_len

        if self._tower:
            self._update_camera(self.platformer.frame.coords.y)

        if string:
            stdout.write(
                self._fill(self._prefix(str(string), self.platformer.icon)) + "\n")

        elif self.platformer.frame.coords in self.platformer.info_msgs:

            info_msg = self.platformer.info_msgs[self.platformer.frame.coords]

            # Reduce screen movement when playing.

            stdout.write(
                self._fill(self._prefix(str(info_msg), "?")) + "\n")

        else:

            title_str = shorten(self.platformer.title.upper(),
                                width=x_len // 3, placeholder="...")

            desc_str = self.platformer.desc
            string = shorten(
                f"[{title_str!s}] {(desc_str if self.display_desc else '')!s}",
                width=x_len, placeholder="...")

            stdout.write(
                self._fill(self._prefix(str(string), self.platformer.icon)) + "\n")

        if self.platformer.timelimit != float("inf"):

            if self.display_coords:
                coord_str = f"Coords: {self.platformer.frame.coords!s}"
            else:
                coord_str = " "

            time_str = self._format_time()

            if not (coord_str.isspace() and time_str.isspace()):
                stdout.write(f"{time_str}{coord_str}\n")

        stdout.flush()

        gmap = self.platformer.maps.game if game_map is None else game_map

        if self._tower:
            stdout.write(str(gmap[self.platformer.slice]))
        else:
            stdout.write(str(gmap))

        if self.platformer.debug:

            dmap = self.platformer.maps.default

            if self._tower:
                stdout.write(str(dmap[self.platformer.slice]))
            else:
                stdout.write(str(dmap))

        stdout.flush()

    def render(self):

        """This will truly handle all rendering for the main loop.
        It will check win
        conditions to figure out whether it should display the win/death
        message.
        Else, it will also print the time."""

        self._render()

        val = self.checker.get_return_value()

        if val is not None:

            stdout.write(val.win_repr + "\n")
            sleep(2)
            return val.status, val.jumps

class Platformer:

    """An object that stores the entire game state
    and has the capability of playing the game.
    It takes in a game map, and also has optional parameters:

    - desc: to be displayed on top of the game.
    - timelimit: A timelimit to beat the game under.
    This is not enforced, but a value is sent out of .play()
    if you finish in time.
    - icon: The player icon. Will raise a ValueError if it
    is a character used inside the game (such as '#'). Default 'O'.
    - debug: A parameter that also displays the default map.
    Default False."""

    __slots__ = (

        # Level Data Object
        "_level_data",

        # Level Data
        "maps",
        "desc",
        "timelimit",
        "title",
        "info_msgs",
        "author",
        "date",

        # Other Parameters
        "icon",
        "debug",
        "meta",
        "display_desc",
        "display_coords",

        # Derived Data
        "start",

        # Current Data
        "frame",

        # Collection Related
        "coin_counter",
        "collected_now",

        # Environment Data
        "keys",
        "portals",
        "stepped_on",
        "locks",

        # Stats
        "jumps",
        "start_time",

        # Booleans
        "down",
        "gravity_changed",
        "teleported",
        "hidden",

        # Other
        "move",
        "renderer",
        # "log_map", # `Log

    )

    def __init__(self, level_data: LevelData, /, *,
                 icon: str="O", debug: bool=False, meta: bool=True,
                 display_desc=True, display_coords=False) -> None:

        """Args:

        level_data: LevelData - The level to be played.
        icon: str='O' - The player icon.
        debug: bool=False - FOR DEVELOPMENT. Displays the default_map
        under the game map while playing.
        """

        self._level_data = level_data.copy()

        if self._level_data == LevelData.NULL:
            return
        elif not self._level_data:
            raise ValueError(f"Corrupted LevelData object {self}")

        title, author, date, desc, game_map, time, info_msgs, _ = level_data

        if time is None:
            time = float("inf")

        if info_msgs is None:
            info_msgs = []

        if desc is None:
            desc = ""

        if icon in CHARS:
            raise ValueError(f"Character {icon!r} reserved for use in maps.")

        self.maps = PlatformerMap(game_map)
        # self.log_map = self.maps.default.copy() # `Log

        self.desc = desc
        self.title = title

        self.start = level_data.start
        self.stepped_on = Asterisks()

        self.frame = ExecutionFrame(AliveCode.ALIVE, self.start.copy())

        self.timelimit = time

        self.author = author
        self.date = date

        self.icon = icon
        self.debug = debug
        self.meta = meta

        self.coin_counter = CoinCounter(total=self.maps.game.count("@"))
        self.collected_now = None

        self.keys = Keys() # lowercase k, UPPERCASE K
        self.locks = Locks(self.maps)
        self._progress_locks()

        self.jumps = 0
        self.start_time = None

        self.hidden = False

        self.portals = Portals(game_map)

        self.move = MovementParameters()

        # Spaces moved:
        # - on x when not sprinting (sx)
        # - on x when sprinting (fx)

        # - on y currently (y)
        # - on y when sprinting (fy)

        self.info_msgs = InfoMsgs.from_memory_efficient(
            self._level_data.info, self.maps.default
        )

        self.down = True

        self.gravity_changed = False

        self.renderer = Renderer(self,
                                 display_desc=display_desc,
                                 display_coords=display_coords
                                 )

        self.display_desc = display_desc
        self.display_coords = display_coords

    @property
    def gravity(self):
        return 1 if self.down else -1

    @gravity.setter
    def gravity(self, val: int):

        if abs(val) == 1:
            self.down = bool(val + 1)

    @property
    def elapsed(self):

        if self.start_time is None:
            return -1.0

        return perf_counter() - self.start_time

    @property
    def time_surpassed(self):

        return self.elapsed > self.timelimit

    @property
    def death_status(self):

        return Status(Result.NONE, float("inf")), self.jumps

    @property
    def null_status(self):
        return Status(Result.NONE, float("inf")), 0

    def _new_move(self, move):

        if self.down:
            return move
        else:

            table = str.maketrans({"w": "s", "s": "w"})
            move = move.translate(table)
            return move

    def _check_item_collection(self, coords: Coordinates):

        """Checks a condition during every tick of movement in
        self._new_position_helper(), self._apply_gravity, etc.
        This condition usually is involved with collecting an item,
        or interacting with a block.

        This function DOES NOT RETURN ANYTHING. It only modifies
        game state."""

        # self.log_map[coords] = self.icon # `Log

        i = self.maps.default[coords]
        match i:

            case "@":
                self.coin_counter.update()
                self.collected_now = True
            case "k" | "K":
                self.collected_now = True
                self.keys.set_char(i, True)
            case "h" | "H":
                self.keys.set_char("k" if i == "h" else "K", False)

            case "/":
                self.hidden = True
            case "\\":
                self.hidden = False

        if self.collected_now:
            self._clear_collectible(coords)

        if i in KEYS:
            self._progress_locks()

    def _affected_frame(self, coords: C) -> ExecutionFrame:

        """Checks a condition during every tick of movement in
        self._new_position_helper(), self._apply_gravity, etc.
        This condition usually is involved with collecting an item,
        or interacting with a block.

        This function RETURNS A FRAME, and also a boolean on whether
        the function did anything. (This is for return type consistency
        and also making the check in the caller function quicker.)"""

        if self.maps.default[coords] == "F":
            return ExecutionFrame(AliveCode.WON, coords), True

        if (self.gravity_changed is False and
                self.maps.default[coords] in GRAVITY):

            self.gravity_changed = True

            return (self._flip_gravity(ExecutionFrame(AliveCode.ALIVE, coords),
                                       self.maps.default[coords]
                                       ), True)

        elif (self.maps.default[coords] in TELEPORT and not self.teleported):

            self.teleported = True
            return (self._teleport(ExecutionFrame(AliveCode.ALIVE, coords)),
                    True)

        elif (self.maps.default[coords] == "$"):

            return (self._launch(coords), True)

        return ExecutionFrame(AliveCode.ALIVE, coords), False

    def _apply_gravity(self, frame):

        """Brings the player down to the floor and applies gravity
        to the player."""

        new = frame.coords.copy()
        below = new.adj("s", self.gravity)

        current_chr = self.maps.game[new]
        chr_below = self.maps.game[below]

        if not frame.alive.is_alive():
            return frame

        self._check_item_collection(new)

        new_frame, changed = self._affected_frame(new)
        if changed:
            return new_frame

        while (NOT_PASSABLE.isdisjoint(MapCharset({chr_below, current_chr})) and
               self.maps.game._bounded(below)):

            new.y -= self.gravity

            below = new.adj("s", self.gravity)

            current_chr, chr_below = self.maps.game[new], self.maps.game[below]

            if self.maps.game[new] == "x":
                return ExecutionFrame(AliveCode.DEAD, new)
            self._check_item_collection(new)

            new_frame, changed = self._affected_frame(new)
            if changed:
                return new_frame

        return ExecutionFrame(AliveCode.ALIVE, new)

    def _top_level_apply_gravity(self, frame):

        frame = self._apply_gravity(frame)
        self.gravity_changed = False
        return frame

    def _new_position_helper(self, move: str, player_coords: C):

        """Finds the new position for the player without taking into
        account the gravity or player interactions.

        Essentially, it moves the player up or down, and then
        left or right."""

        move = self._new_move(move)

        new = player_coords.copy().as_normal()
        o = player_coords.copy().as_normal()

        # For going down.
        if (len(move) == 2 and "s" in move and
                self.maps.game._bounded(new.adj("s"))):
            new.y -= self.gravity

        match move:

            case "w":

                if (new.y + self.gravity) >= self.maps.game.y_len:
                    return ExecutionFrame(AliveCode.ALIVE, o)

                current_chr = self.maps.game[o]
                chr_above = self.maps.game[C(new.x, new.y + self.gravity)]

                # Climbing up a ladder, move up once and stop.
                if "_" in {current_chr, chr_above}:
                    new.y += self.gravity
                    return ExecutionFrame(AliveCode.ALIVE, new)

                # Move up.

                while (chr_above not in HARD and abs((new - o).y) < self.move.Y
                       and self.maps.game._bounded(new.adj("w", self.gravity))):

                    new.y += self.gravity

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)
                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                    chr_above = self.maps.game[new.adj("w", self.gravity)]

            case "s":

                # Move down.
                if (self.maps.game[new.adj("s")] not in HARD
                        and self.maps.game._bounded(new.adj("s"))):
                    new.y -= self.gravity

            case "a":

                left = new.adj("a", self.gravity)

                # Move left
                while (
                        (
                                self.maps.game[left] not in HARD
                                or left.as_frozen() in self.stepped_on
                        )
                        and self.maps.game._bounded(left)
                        and abs((new - o).x) < SLOW_X
                ):

                    new.x -= 1

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)

                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                    left = new.adj("a", self.gravity)

            case "d":

                right = new.adj("d", self.gravity)

                # Move right
                while (
                        (
                                self.maps.game[right] not in HARD
                                or right.as_frozen() in self.stepped_on
                        )
                        and self.maps.game._bounded(right)
                        and abs((new - o).x) < SLOW_X
                ):

                    new.x += 1

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)
                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                    right = new.adj("d", self.gravity)

            case "aw" | "wa":

                above = new.adj("w", self.gravity)

                # Move up
                while (
                        self.maps.game[above] not in HARD
                        and abs((new - o).y) < self.move.Y
                        and self.maps.game._bounded(above)
                ):

                    new.y += self.gravity
                    above.y += self.gravity

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)
                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                left = new.adj("a", self.gravity)
                top = o.copy() + C(0, self.gravity)
                below = new.adj("s", self.gravity)

                o = new.copy()

                # Move to the side
                while (
                        self.maps.game[left] not in HARD
                        and self.maps.game._bounded(left)
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    # Stop if jumping over an obstacle
                    # that is same height as player's jump height.

                    if (self.maps.game[top] in HARD
                            and self.maps.game[below] in HARD):
                        break

                    new.x -= 1
                    left.x -= 1
                    below.x -= 1
                    top.x -= 1

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)

                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

            case "dw" | "wd":

                above = new.adj("w", self.gravity)

                # Move up
                while (
                        self.maps.game[above] not in HARD
                        and abs((new - o).y) < self.move.Y
                        and self.maps.game._bounded(above)
                ):

                    new.y += self.gravity
                    above.y += self.gravity

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)
                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                right = new.adj("d", self.gravity)
                top = o.copy() + C(0, self.gravity)
                below = new.adj("s", self.gravity)

                o = new.copy()

                # Move to the side
                while (
                        self.maps.game[right] not in HARD
                        and self.maps.game._bounded(right)
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    # Stop if jumping over an obstacle
                    # that is same height as player's jump height.

                    if (self.maps.game[top] in HARD
                            and self.maps.game[below] in HARD):
                        break

                    new.x += 1
                    right.x += 1
                    below.x += 1
                    top.x += 1

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

            case "as" | "sa" | "aa" | "a'" | "'a'":

                left = new.adj("a", self.gravity)

                # Move left
                while (
                        (
                                self.maps.game[left] not in HARD
                                or left.as_frozen() in self.stepped_on
                        )
                        and self.maps.game._bounded(left)
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    new.x -= 1

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)

                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                    left = new.adj("a", self.gravity)

            case "ds" | "sd" | "dd" | "d'" | "'d'":

                right = new.adj("d", self.gravity)

                # Move right
                while (
                        (
                                self.maps.game[right] not in HARD
                                or right.as_frozen() in self.stepped_on
                        )
                        and self.maps.game._bounded(right)
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    new.x += 1

                    if self.maps.game[new] == "x":
                        return ExecutionFrame(AliveCode.DEAD, new)
                    elif self.maps.game[new] in STOP:
                        return ExecutionFrame(AliveCode.ALIVE, new)

                    self._check_item_collection(new)

                    new_frame, changed = self._affected_frame(new)
                    if changed:
                        return new_frame

                    right = new.adj("d", self.gravity)

        return ExecutionFrame(AliveCode.ALIVE, new)

    @staticmethod
    def _gravity_affected(top_level=True):

        def decorator(func):

            @wraps(func)
            def wrapper(self: Platformer, *args, **kwargs):

                r = func(self, *args, **kwargs)

                if not isinstance(r, ExecutionFrame):
                    raise ValueError(
                        f"Function {func.__name__} did not return execution frame.")

                # if needed bool
                if isinstance(r.apply_grav, bool) and r.apply_grav:

                    grav = (self._top_level_apply_gravity
                            if top_level else self._apply_gravity)

                    r = grav(r)

                r.coords = r.coords.as_normal()

                return r

            return wrapper

        return decorator

    @_gravity_affected(top_level=False)
    def _check_countdown_collision(self, frame):

        alive = frame.alive

        if self.maps.default[frame.coords] in COUNTDOWN:

            alive = AliveCode.DEAD

        return ExecutionFrame(alive, frame.coords, True)

    def _check_platform_collision(self, frame):

        coords = frame.coords.as_normal()

        adj = partial(coords.adj, g=self.gravity)

        coord_under = self.maps.game[adj("s")]

        # A bunch of coords to make comparisons cleaner.
        coord_left = self.maps.game[adj("sa")]
        coord_right = self.maps.game[adj("sd")]
        coord_dunder = self.maps.game[adj("ss")]
        coord_above = self.maps.default[adj("w")]

        current = self.maps.default[coords]

        dead = AliveCode.ALIVE

        ARROWS, BELTS = MapCharset("V^<>"), MapCharset("|-")
        HARD_NO_ARROWS = (HARD - ARROWS) | MapCharset("x")

        TRANSPARENT_WITH_ARROWS = TRANSPARENT | ARROWS | BELTS | MapCharset("_")
        g1 = "V" if self.down else "^"
        g2 = "^" if self.down else "V"

        gravity_needed = True

        g = self.gravity if coord_dunder in "|V^" else -self.gravity

        match coord_under:

            case "<":
                coords.x -= 1 if coord_left in "-<>" else -1
            case ">":
                coords.x += 1 if coord_right in "-<>" else -1
            case i if i == g1:
                coords.y -= g

            case i if i == g2 and current != "_":

                # Reached the top of the platform belt.

                if current in TRANSPARENT:
                    coords.y -= self.gravity

                # All other conditions from here mean the icon
                # is still moving

                # Crash into the top of the map. Icon disappears.

                elif not self.maps.game._bounded(adj("w")):

                    self.maps.both[coords] = "|"
                    dead = AliveCode.DEAD
                    self.hidden = True

                elif coord_above in HARD_NO_ARROWS:

                    coords.y += self.gravity
                    dead = AliveCode.DEAD

                elif coord_above in TRANSPARENT_WITH_ARROWS:

                    # Move up: upper character is not hard.
                    coords.y += self.gravity

            case _:
                gravity_needed = False

        return ExecutionFrame(dead, coords, gravity_needed)

    def _progress_countdown(self, frame):

        self.maps.update_countdown_blocks()
        frame = self._check_countdown_collision(frame)

        return frame

    @_gravity_affected()
    def _progress_platforms(self, frame):

        """The main function that handles platform generation and
        replacement. It moves all the platforms using the
        other helper functions, and moves the player with it
        if they are on top of a platform."""

        frame = self._check_platform_collision(frame)
        self.maps.update_platforms()

        return frame

    def _progress_locks(self, *, only_not=False):

        """Handles removing the locks in the grid if
        a key was collected."""

        for i, lock, not_lock in zip("kK", "lL", "nN"):

            if only_not is False:
                self.locks.edit(lock, self.keys.get_char(i))

            self.locks.edit(not_lock, not self.keys.get_char(i))

        if only_not:
            return

        self.locks.edit("A", all(self.keys))
        self.locks.edit("X", self.keys.k != self.keys.K)

    @_gravity_affected(top_level=False)
    def _launch(self, coords):

        self.hidden = True

        x_radius = 6
        y_radius = 6

        x, y = coords
        launch_coords = coords.copy()

        # Local display
        current_map = self.maps.game.copy()

        top_y = self.maps.game.y_len - 1
        top_x = self.maps.game.x_len - 1

        # Bounds for moving around.
        lower_x = max(x - x_radius, 0)
        upper_x = min(x + x_radius, top_x)

        lower_y = min(max(y, 0), top_y)
        upper_y = max(min(y + self.gravity*y_radius, top_y), 0)

        if not self.down:
            lower_y, upper_y = upper_y, lower_y

        display = current_map.copy()
        old_coords = None

        while True:

            # Switch direction of jumping
            f = "a" if launch_coords.x < x else "d"

            prev_display = display
            display = current_map.copy()

            for i in C.arc(coords, launch_coords):

                if display[i] in HARD:
                    display = prev_display
                    launch_coords = old_coords
                    break

                elif display[i] not in INTERRUPT:
                    display[i] = "!"

            display[launch_coords] = self.icon

            clear()
            self.renderer._render(display, string="Launch!")
            old_coords = launch_coords.copy()

            move = IOUtils.input(
                "Select where to launch ([wasd]/[x] to drop). ")

            # Move around.
            match move:
                case "w":
                    launch_coords.y += 1
                case "s":
                    launch_coords.y -= 1
                case "a":
                    launch_coords.x -= 1
                case "d":
                    launch_coords.x += 1
                case "x": # Finished

                    self.hidden = False

                    for i in C.arc(coords, launch_coords):
                        self.maps.both.patch(i)

                    clear()

                    # Works like vector subtraction.
                    # Note: absolute value works component-wise

                    dx, dy = abs(launch_coords - coords)

                    # Swap game movement parameters for jump.
                    move = self.move
                    self.move = MovementParameters(dx, dy)
                    launch_move = self._new_move(f"w{f}")
                    frame = self._new_position_helper(launch_move, coords)
                    self.move = move

                    return frame

            # Bound coords
            launch_coords.x = max(min(launch_coords.x, upper_x), lower_x)
            launch_coords.y = max(min(launch_coords.y, upper_y), lower_y)

            if display[launch_coords] in HARD:
                launch_coords = old_coords

    @_gravity_affected(top_level=False)
    def _teleport(self, frame):

        try:
            possible_coords = self.portals[frame.coords]
        except KeyError:
            return ExecutionFrame(AliveCode.ALIVE, frame.coords)

        num_found = len(possible_coords)

        if num_found == 1:
            return ExecutionFrame(AliveCode.ALIVE,
                                  possible_coords[0].as_normal())
        else:

            possible_coords_x = sorted(possible_coords,
                                       key=lambda c: (c.x, c.y))
            possible_coords_y = sorted(possible_coords,
                                       key=lambda c: (c.y, c.x))

            current_map = self.maps.game.copy()
            current_ind_x = 0
            current_ind_y = possible_coords_y.index(possible_coords_x[0])

            self.hidden = True
            while True:

                display = current_map.copy()
                c = possible_coords_x[current_ind_x].as_normal()

                for coord in c.adjs("w", "a", "s", "d", g=self.gravity):
                    display[coord] = "!"

                clear()
                self.renderer._render(display)

                move = IOUtils.input(
                    "Select where to teleport ([wasd]/[ENTER]). ")

                match move:

                    case "a" | "d":

                        current_ind_x += 1 if move == "d" else -1
                        current_ind_x %= num_found
                        current_ind_y = possible_coords_y.index(
                            possible_coords_x[current_ind_x])

                    case "w" | "s":

                        current_ind_y += 1 if move == "w" else -1
                        current_ind_y %= num_found
                        current_ind_x = possible_coords_x.index(
                            possible_coords_y[current_ind_y])

                    case "":

                        self.maps.both.patch(frame.coords)
                        clear()
                        self.hidden = False
                        return ExecutionFrame(AliveCode.ALIVE, c)

                current_ind_x %= num_found
                current_ind_y %= num_found

    def _new_position(self, move: str):

        """Finds the new position for the player."""

        frame = ExecutionFrame(AliveCode.ALIVE, self.frame.coords)

        if not frame.alive.is_alive():
            return frame

        if self._check_item_collection(frame.coords):
            return ExecutionFrame(AliveCode.WON, frame.coords)

        frame = self._new_position_helper(move, self.frame.coords.copy())

        if not frame.alive.is_alive():
            return frame

        if self._check_item_collection(frame.coords):
            return ExecutionFrame(AliveCode.WON, frame.coords)
        else:

            new_frame, changed = self._affected_frame(frame.coords)
            if changed:
                return new_frame

        frame = self._top_level_apply_gravity(frame)

        if not frame.alive.is_alive():
            return frame

        if self._check_item_collection(frame.coords):
            return ExecutionFrame(AliveCode.WON, frame.coords)
        else:

            new_frame, changed = self._affected_frame(frame.coords)
            if changed:
                return new_frame

        return frame

    @_gravity_affected(top_level=False)
    def _flip_gravity(self, frame, char: Literal["+", "="], func=None):

        self.down = False if char == "+" else True
        return frame

    def _progress_helper(self, move: str) -> ExecutionFrame:

        """Finds the new coordinates after a move, using a current move
        as well as information from asterisks. It uses algorithms that
        traces the path of the character while also determining when to
        stop, updating the player coordinates accordingly.

        It also does much more than this, managing the game state and
        flow of the program. This function is called every tick, so
        it is designed for optimization. (Or at least, it is hopefully
        optimized.) That is why so many caches are used for map updates.
        """

        self.stepped_on.clear()
        original = self.frame.coords.copy()

        # --- Initial new position ---

        frame = self._new_position(move)

        if not frame.alive.is_alive():
            return frame

        # --- Initial new position <end> ---

        self._check_item_collection(frame.coords)
        frame, _ = self._affected_frame(frame.coords)

        self.stepped_on.populate(self, frame)

        # --- Map Updates ---

        frame = self._progress_platforms(frame)

        if not frame.alive.is_alive():
            return frame

        frame = self._progress_countdown(frame)

        if not frame.alive.is_alive():
            return frame

        # --- Map Updates <end> ---

        # --- Teleport ---

        # --- Teleport <end> ---

        self._check_item_collection(frame.coords)
        frame, _ = self._affected_frame(frame.coords)

        self.stepped_on.populate(self, frame)

        # --- Some extra conditions ---

        i = self.maps.default[frame.coords]

        match i:
            case "\\":
                self.hidden = False
            case "/":
                self.hidden = True

        # --- Some extra conditions <end> ---

        # --- Get final frame ---

        match self.maps.game[frame.coords]:

            case i if i in HARD:
                val = ExecutionFrame(AliveCode.ALIVE, original)
            case "F":
                val = ExecutionFrame(AliveCode.WON, frame.coords)
            case "x":
                val = ExecutionFrame(AliveCode.DEAD, frame.coords)
            case _:
                val = ExecutionFrame(AliveCode.ALIVE, frame.coords)

        # --- Get final frame <end> ---

        return val

    def _progress(self, move: str) -> ExecutionFrame:

        self._clear_items()

        frame = self._progress_helper(move)

        if not self.hidden:
            self.maps.game[frame.coords] = self.icon

        self.gravity_changed = False
        self.teleported = False

        if self._check_item_collection(frame.coords):
            return ExecutionFrame(AliveCode.WON, frame.coords)

        return frame

    def _clear_collectible(self, coord=None):

        if not self.collected_now:
            return

        if coord is None:
            coord = self.frame.coords

        self.maps.clear_coord(coord)
        self.collected_now = False

    def _clear_items(self):

        """Clears the coins as well as the character."""

        self._clear_collectible()
        self.maps.clear_asterisks(self.stepped_on)

        if not self.collected_now:
            self.maps.both.patch(self.frame.coords)

    def _restart(self):

        """Resets all the attributes and game state."""

        self.__init__(self._level_data.copy(),
                      icon=self.icon,
                      debug=self.debug,
                      meta=self.meta,
                      display_desc=self.display_desc,
                      display_coords=self.display_coords
                      )

        self.start_time = perf_counter()
        self._prepare_game()

        self.maps.clear_asterisks(self.stepped_on)

    def _pause(self, a: float, *, print_desc=False):

        """Pauses the game."""

        clear()

        desc = self.desc

        if print_desc:

            self.renderer.print_desc()
        else:
            self.renderer._render(string="[||] PAUSED")

        IOUtils.input("[|>] Resume? ")
        b = perf_counter()
        self.start_time += (b - a)
        self.desc = desc

        # Getting back to the game.
        clear()

    def _parse_move(self, a: float, move: str):

        """Parses the user's move, whether it
        is:
        - playing the game (moving)
        - restarting
        - exiting
        - pausing
        """

        match IOUtils.sanitized(move):

            case "restart" | "r":
                clear()
                self._restart()
                return True

            case "exit" | "x":
                return self.death_status

            case "p" | "pause":
                clear()

                self._pause(a)
                return True

            case "desc" | "e" if (self.desc or self.meta):

                self._pause(a, print_desc=True)
                return True

            case _:
                clear()
                self.frame = self._progress(move)
                self.jumps += 1

    def _prepare_game(self):

        self.maps.game[self.frame.coords] = self.icon
        self.start_time = perf_counter()
        clear()

    def play(self) -> tuple[Status, int]:

        """Plays the Platformer object, and sends out the results
        if the player wins or loses."""

        if self._level_data == LevelData.NULL:
            return self.null_status

        self._prepare_game()

        while True: # Game Loop

            data = self.renderer.render()

            if data:
                return data

            data = self._parse_move(perf_counter(),
                                    IOUtils.input("-> "))

            # logger.debug(self.title + "\n" + str(self.log_map) + "\n") # `Log
            # self.log_map = self.maps.default.copy() # `Log

            if data is True:
                continue
            elif data is not None:
                return data

################################################################################

class Tower(Platformer):

    """A class for the final level, which is way taller
    (it's a tower, obviously) and also implements camera
    tracking the player so it keeps the 63 x 12 screen dimensions.
    This mode can also be extended to custom-made levels with
    any height, though it has not been tested."""

    slots = ("bottom", "top", "screen_len")

    def __init__(self, level_data: LevelData, *, icon: str="O",
                 debug: bool=False, meta: bool=True,
                 display_desc: bool=True, display_coords: bool=False):

        super().__init__(level_data,
                         icon=icon, debug=debug, meta=meta, display_desc=display_desc,
                         display_coords=display_coords
                         )

        self.bottom = 0
        self.top = self.maps.game.y_len - 1
        self.screen_len = Constants.Y_LEN

    @property
    def slice(self):

        return slice(self.bottom, self.top, None)

class MapGenerator:

    __slots__ = ("e", "total_iterations", "new_data", "frames", "debug",
                 "_POSSIBLE_MOVES")

    def __init__(self, endless: Endless, debug=False):

        self.e = endless
        self.total_iterations = 0
        self.new_data = None
        self.frames = []
        self.debug = debug

        self._POSSIBLE_MOVES = [
            "wd",
            "d'",
            "d",
            "sd",
            "s",
            "",
            "wa",
            "a'",
            "w",
            "sa",
            "a",

        ]

        if self.e.mode == 1:
            self._POSSIBLE_MOVES.remove("")

    def _generate_rough_map(self):

        """Creates a map based on parameters that may or may
        not be impossible. It uses Perlin Noise along a line
        to get subtle up and downs. These values are then augmented
        and plotted on the map relative to the line y=4.
        The ground is filled below, and spikes/asterisks may
        be added on top."""

        game_map = GameMap.solid(" ")

        def perlin():

            y = 4
            char = "#"

            noise = PerlinNoise()

            vals = []
            for x in range(Constants.X_LEN):

                val = noise.noise(x + random(), y + random())
                relative_val = y + (val * self.e.stretch)
                vals.append(int(relative_val))

            for x, i in enumerate(vals):
                for new_y in range(i, -1, -1):
                    if new_y >= 0:
                        game_map[C(x, new_y)] = char

        perlin()

        def check_seq(lst, i, length=4) -> bool:

            val = lst[i]
            seq = True

            for j in range(1, length):
                if lst[i+j] != val + j:
                    seq = False

            return seq

        def vertical():
            return range(Constants.Y_LEN - 1, 0, -1)

        def down(coord):

            return coord.adj("s", 1)

        while True:
            spike_indices = sorted(sample(range(Constants.X_LEN), k=self.e.spikes))
            for i in range(self.e.spikes - 3):
                if check_seq(spike_indices, i):
                    continue
            break

        for x in spike_indices:
            if x not in {3, Constants.X_LEN - 2}:
                for y in vertical():
                    coord = C(x, y)

                    if game_map[down(coord)] == "#":
                        game_map[coord] = "x"
                        break

        if self.e.mode == 2:
            ast_indices = sample(range(Constants.X_LEN), k=self.e.asterisks)
            for x in ast_indices:
                if x not in {3, Constants.X_LEN - 2}:
                    for y in vertical():
                        coord = C(x, y)

                        if game_map[down(coord)] in MapCharset("#x"):
                            game_map[coord] = "*"
                            break

        for y in vertical():
            coord = C(3, y)

            if game_map[down(coord)] == "#":
                game_map[coord] = "S"
                start = coord
                break

        else:
            start = C(3, 0)

        for y in vertical():

            coord = C(Constants.X_LEN - 2, y)
            if game_map[down(coord)] == "#":
                game_map[coord] = "F"
                finish = coord
                break
        else:
            finish = C(Constants.X_LEN - 2, 0)

        return game_map.copy(), start, finish

    def _swap(self, coords):

        self.e.frame.coords, coords = coords, self.e.frame.coords

    def _new_frame(self, move, coords) -> ExecutionFrame:

        coords = coords.as_normal()

        self._swap(coords)
        frame = self.e._progress(move)
        self._swap(coords)

        return frame

    def _is_valid_move(self, move: str, coords: Coordinates):

        """Returns the death status and new coordinates
        based on a move from a current coordinate."""

        frame = self._new_frame(move, coords)

        if (frame.alive == AliveCode.DEAD
                or self.e.maps.default[frame.coords] == "x"):
            return ExecutionFrame(AliveCode.DEAD, frame.coords.as_frozen())

        elif self.e.maps.default[frame.coords] in HARD:
            return ExecutionFrame(AliveCode.ALIVE, coords)

        frame.coords = frame.coords.as_frozen()

        return frame

    def _is_possible_map(self, game_map, current, finish,
                         visited=None):

        """Recursive function to determine if a function is
        possible. Starting from start, it plays all combinations
        of jumps until it finds one that goes from start to finish."""

        if visited is None:
            visited = set([current.as_frozen()])

        for move in self._POSSIBLE_MOVES:
            frame = self._is_valid_move(move, current)
            f = frame.coords

            if frame.alive == AliveCode.DEAD or f in visited:

                # Stop recursion. Dead or in cycle.
                continue

            elif f == finish.as_frozen():

                # Reached finish, terminate search.

                if self.debug:
                    frame = game_map.copy()
                    frame[current] = self.e.icon
                    self.frames.append(frame)

                return True

            else:

                visited.add(f)
                new_result = self._is_possible_map(game_map, frame.coords,
                                                   finish, visited)

                if new_result is True: # Reached finish later in recursion.

                    if self.debug:
                        frame = game_map.copy()
                        frame[current] = self.e.icon
                        self.frames.append(frame)

                    return True

        return False

    def _level_data_from_map(self, new_map: GameMap):

        title = f"Stage {self.e.level}"

        return LevelData(
            title=title,
            map=new_map.copy(),
            info=MemoryEfficientInfoMsgs()
        )

    def generate_map(self, speed=0.5):

        """Generates a possible map and returns the map."""

        local_iterations = 0
        while True:

            self.frames.clear()

            local_iterations += 1
            self.total_iterations += 1

            data = self._generate_rough_map()

            new_map, self.e.frame.coords, *_ = data

            self._populate_attrs_with_map(new_map)
            possible = self._is_possible_map(*data)

            if possible:

                if self.debug:
                    self.frames = reversed(self.frames)

                    for i in self.frames:
                        clear()
                        stdout.write(str(i))
                        sleep(speed)

                    clear()

                new_data = self._level_data_from_map(new_map)
                self.new_data = new_data

                return new_data

            if self.total_iterations == 1_000:
                stdout.write(
                    "Hang on tight! We're working on getting the map for you!\n")

            if local_iterations >= 500:
                local_iterations = 0
                self.e.parameters.stretch -= 0.1 # Make generation easier

    def _populate_attrs_with_map(self, new_map):

        if new_map is not None:
            self.e.maps = PlatformerMap(new_map)
            self.e.locks = Locks(self.e.maps)
            self.e.portals = Portals(new_map)

    def __enter__(self):

        self.e.frame = ExecutionFrame(AliveCode.ALIVE, C(0, 0))

        self.e.keys = Keys()

        self.e.collected_now = False

        self.e.stepped_on = Asterisks()
        self.e.hidden = True
        self.e.down = True
        self.e.gravity_changed = False

        self.e.move = MovementParameters()

        return self

    def __exit__(self, exc_type, exc_value, traceback):

        if self.new_data is None:
            raise Exception("Map generation failed")

        for attr in Platformer.__slots__:

            try:
                delattr(self.e, attr)
            except AttributeError:
                continue

@dataclass(slots=True)
class GenerationParameters:

    stretch: float=1
    spikes: int=8
    mode: Literal[1, 2]=1
    asterisks: int=1

    def __iter__(self):

        return iter(astuple(self))

    @classmethod
    def from_mode(cls, mode: Literal[1, 2]):

        if mode == 1:
            return cls(1, 8, 1, 0)
        elif mode == 2:
            return cls(1, 8, 2, 10)

    @property
    def level(self):
        return int((self.stretch - 1) * 10) + 1

    def __next__(self):

        stretch = self.stretch + 0.1
        spikes = min(self.spikes + 1, Constants.X_LEN // 2)

        if self.mode == 2:
            asterisks = min(self.asterisks + 1, Constants.X_LEN // 2)
        else:
            asterisks = self.asterisks

        return type(self)(stretch, spikes, self.mode, asterisks)

class Endless(Platformer):

    __slots__ = (
        "parameters",
    )

    def __init__(self,
                 parameters: GenerationParameters, *,
                 icon: str="O", debug: bool=False, _level_data: bool=None,
                 display_coords: bool=False):

        self.parameters = parameters

        self.icon = icon
        self.debug = debug
        self.display_coords = display_coords

        if _level_data is None:

            with MapGenerator(self, debug=False) as gen:
                data = gen.generate_map(speed=0.15)

        else:
            data = _level_data.copy()

        super().__init__(data, icon=icon, debug=debug, meta=False,
                         display_desc=False, display_coords=display_coords)

    @property
    def stretch(self):
        return self.parameters.stretch
    @property
    def spikes(self):
        return self.parameters.spikes
    @property
    def mode(self):
        return self.parameters.mode
    @property
    def asterisks(self):
        return self.parameters.asterisks
    @property
    def level(self):
        return self.parameters.level

    def _restart(self):

        """New, overwritten restart, because Endless has different
        args than Platformer in __init__."""

        self.__init__(
            self.parameters,
            icon=self.icon, debug=self.debug, _level_data=self._level_data,
            display_coords=self.display_coords
        )

        self.start_time = perf_counter()
        self._prepare_game()
