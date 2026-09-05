from __future__ import annotations

from typing import Literal, Optional, Callable
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

HARD = MapCharset("#*LlAnNX<>V^123456789%")
NOT_PASSABLE = MapCharset("#*LlAnNX<>V^123456789_%")
TRANSPARENT = MapCharset(" :'\"Kk?`()[]{}/\\+=$@SF;.,")

LOCKS = MapCharset("lLAnNX")
KEYS = MapCharset("KkHh")
COLLECTIBLES = MapCharset("Kk@")
COUNTDOWN = MapCharset("123456789")
ARROWS = MapCharset("<>^V")
HORIZONTAL = MapCharset("-<>")
VERTICAL = MapCharset("|^V")
GRAVITY = MapCharset("+=")
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

        return f"Status(result={self.result!r}, time={self.time:3f})"

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
    
    def is_dead(self):

        """Returns whether the player is dead
        (self == AliveCode.DEAD). Is false
        when the player has won or is alive."""

        return self.value == 0

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

    def freeze(self):
        self.coords = self.coords.as_frozen()

    def normalize(self):
        self.coords = self.coords.as_normal()

@dataclass
class CoinCounter:

    """A class that tracks the total number of coins
    in a map, as well as the amount the player
    has collected. The update method adds 1
    to the counter if there are still coins left.
    The full property returns whether the player
    has collected all coins."""

    __slots__ = ("total", "collected")

    total: int

    def __post_init__(self):

        self.collected: int = 0

    def __str__(self):

        return f"{self.collected}/{self.total}"

    def update(self):

        if not self.full:
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

    """A generator class that, given an initial game map,
    calculates the next position of the moving arrow platforms
    and their directions. Additionally, after next() is called,
    the generator object saves the result as self.last_value."""

    __slots__ = ("game_map", "last_value")

    def __init__(self, game_map: GameMap):

        self.game_map = game_map
        self.last_value = Cells.from_map(game_map, ARROWS)

    def __next__(self) -> Cells:

        result = Cells()

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

            result.add(Cell(FrozenC(x, y), new_dir))

        self.last_value = result

        return result

    def __iter__(self):
        return self

class CountdownGenerator:

    """A generator class that, given an initial game map,
    calculates the values of the countdown blocks at their
    coordinates."""

    __slots__ = ("iterators",)

    def __init__(self, game_map: GameMap):

        self.iterators = dict()

        for coord, char in Cells.from_map(game_map, COUNTDOWN):

            r = [(str(num) if num != 0 else "`") for num in range(int(char), -1, -1)]
            iterator = cycle(r)

            # Map already contains first position, skip to second
            next(iterator)

            self.iterators[coord] = iterator

    def __next__(self) -> Cells:

        return Cells({
            Cell(coord, next(iterator)) for coord, iterator in
            self.iterators.items()
        })

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

    def __iter__(self):

        return iter(self.locks)

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

    """A class that defines how a player moves in-game.
    FAST_X is how far a player moves when they jump.
    Y is the height a player reaches when they jump.
    Both variables are set on default to the FAST_X
    and Y constants at the top of the file."""

    FAST_X: int = FAST_X
    Y: int = Y

    def reset(self):
        self.FAST_X = FAST_X
        self.Y = Y

class PlatformerMap:

    """A class that provides an interface with two layered maps:
    a game map (with the character) and a default map (no character). In
    fact, at any time, the game map is just the default map with the
    player's icon. The default map serves as context or as a live
    background which the icon is placed on top of. This is
    useful when the icon is cleared and moved every tick.

    Additionally, the class contains in-built control for
    countdown blocks, platforms, locks, and asterisks."""

    __slots__ = ("both", "countdown_gen", "platform_gen")

    def __init__(self, game_map: GameMap):

        self.both = MultiMap(game_map.copy(), game_map.copy())

        self.countdown_gen = CountdownGenerator(game_map)
        self.platform_gen = PlatformGenerator(game_map)

    @property
    def game(self):
        return self.both.game_map

    @property
    def default(self):
        return self.both.default_map

    def clear(self, coord: Coordinates):

        self.both[coord] = " "

    def update_locks(self, locks: Locks):

        for lock in locks:
            coords, open = locks[lock], locks.is_open(lock)

            for coord in coords:
                self.both[coord] = "`" if open else lock

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

        for coord in stepped_on:
            self.clear(coord)

@dataclass(frozen=True)
class WinCondition:

    """A dataclass that stores information on whether the player has
    won or lost. The win_repr attribute is a formatted string
    of the user's death / win."""

    win_repr: str
    status: Status
    jumps: int

class WinDeathChecker:

    """Checks whether the user has won or lost every tick
    and creates a formatted string printed at the
    end of the game if so. The object has one main
    method, get_return_value which returns
    a WinCondition object if the user has won or lost,
    or None if not."""

    __slots__ = ("p",)

    def __init__(self, platformer: Platformer):

        self.p = platformer

    @property
    def result(self) -> Result | None:

        if self.p.frame.alive.is_alive():
            return

        if self.p.frame.alive.is_dead():
            return Result.NONE

        res = Result.WON

        if self.p.coin_counter and self.p.coin_counter.full:
            res |= Result.COIN

        if self.p.timelimit != float("inf") and not self.p.time_surpassed:
            res |= Result.TIME

        return res

    def _win_str(self):

        res = self.result

        win_repr = "Won [+]"

        total = self.p.coin_counter.total

        if total > 1:
            coin_str = f" Coins [{self.p.coin_counter!s}]"
        elif total == 1:
            coin_str = f" Coin [{'+' if Result.COIN in res else 'x'}]"
        else:
            coin_str = ""

        win_repr += coin_str

        if self.p.timelimit != float("inf") and not self.p.time_surpassed:
            time_str = " Time [+]"

        elif self.p.timelimit != float("inf"):
            time_str = " Time [x]"
        else:
            time_str = ""

        win_repr += time_str
        win_repr += f" [{self.p.elapsed:.2f}]"

        return WinCondition(win_repr, Status.from_plat(self.p, res), self.p.jumps)

    def _loss_str(self):

        win_repr = "Won [x] "

        total = self.p.coin_counter.total

        if total > 1:
            coin_str = "Coins [x] "
        elif total == 1:
            coin_str = "Coin [x] "
        else:
            coin_str = ""

        win_repr += coin_str

        win_repr += "" if self.p.timelimit == float("inf") else "Time [x] "
        win_repr += "[You died!]"

        return WinCondition(win_repr, *self.p.death_status)

    def get_return_value(self) -> WinCondition | None:

        """Returns a WinCondition object that contains data
        on whether the player has won or lost. In the case
        that the player is still alive, nothing is returned."""

        if self.result is None:
            return
        if self.result == Result.NONE:
            return self._loss_str()
        else:
            return self._win_str()

@dataclass(frozen=True, slots=True)
class Camera:

    x_len: int | None=None
    y_len: int | None=None

class Renderer:

    """A class that handles rendering the game every tick."""

    __slots__ = (
        "platformer",
        "checker",)

    def __init__(self, platformer: Platformer):

        self.platformer = platformer

        self.checker = WinDeathChecker(platformer)

    @property
    def display_desc(self):
        return self.platformer.display_desc

    @property
    def display_coords(self):
        return self.platformer.display_coords

    @property
    def display_percentage(self):
        return self.platformer.display_percentage

    @property
    def level_data(self):
        return self.platformer._level_data

    @property
    def start(self):
        return self.platformer._level_data.start

    @property
    def finish(self):
        return self.platformer._level_data.finish

    @property
    def text_length(self) -> int:

        """Returns the number of newlines covered by the text displayed
        above the time and the map in Platformer mode.
        This takes into account things like info messages, the title
        and description, following the exact formatting patterns
        used in the Platformer mode.

        This is important as the text length dictates the exact space
        taken up by messages above the map. This allows headers to be
        padded with that many newlines, preventing the game map from
        jittering around with new messages."""

        if self.level_data == LevelData.NULL:
            return -1

        new_title = shorten(self.level_data.title.upper(),
                            width=(self.level_data.map.x_len // 3),
                            placeholder="..."
                            )

        formatted_desc = shorten(
            f"[{new_title!s}] {(self.level_data.desc if self.display_desc else '')!s}",
            width=self.level_data.map.x_len, placeholder="..."
        )

        # All possible text displayed at the top of the screen
        # in Platformer game mode.

        txts = [
            formatted_desc,
            *self.level_data.info,
            "[||] PAUSED",
            "Launch!"
        ]

        # Add the prefix 'O |', '? |', etc. you see at the top
        # of the screen in Platformer mode.
        # Also removes newlines.

        txts = map(lambda txt: f"@ | {txt}".replace("\n", ""), txts)

        # Find the maximum number of newlines any of these strings take
        # up when wrapped.

        return max(len(wrap(txt, width=self.level_data.map.x_len+2)) for txt in txts)

    def fill(self, string: str) -> str:

        """Pads a string displayed above the map with newlines to the map's
        text_length, as well as wrapping the string to the length
        of the screen. This prevents the screen jittering up and down
        as the number of newlines in the above text changes."""

        string = wrap(string.replace("\n", ""),
                      width=self.platformer.maps.game.x_len+2)

        # Number of newlines to pad with
        difference = self.text_length - len(string)

        return "\n".join(string) + ("\n" * difference)

    @property
    def time_str(self):

        """Returns a formatted representation of the time.
        If there is no time limit to the map, then this property
        returns an empty string."""

        if self.platformer.timelimit == float("inf"):
            return ""

        elapsed, timelimit = self.platformer.elapsed, self.platformer.timelimit

        # Exclamation mark if timelimit is exceeded, to give a sense of urgency
        exc = (" (!)" if elapsed > timelimit else "")

        return f"Time: <{elapsed:.2f}|{timelimit:.2f}>{exc}"

    @property
    def coord_str(self):

        """Returns a formatted string containing the player's
        coordinates."""

        if not self.display_coords:
            return ""

        return f"Coords: {self.platformer.frame.coords!s}"

    @property
    def percentage_str(self):

        """Returns a formatted percentage of the way to the finish.
        If there are multiple finish locations, it uses the
        shortest existing distance to a location."""

        if not self.display_percentage:
            return ""

        coords = self.platformer.frame.coords

        closest_finish = min(self.finish, key=lambda x: (x - coords).norm)

        min_distance = (coords - closest_finish).norm
        distance = (self.start - closest_finish).norm

        percentage = 1.0 - min(1.0, min_distance / distance)

        return f"<{percentage:.0%}>"

    @property
    def stats_bar(self):

        """Returns the bar of stats that exists above the game map,
        displaying the time, coords, and percentage. If the map
        does not have a time limit or the settings for any of the
        pieces of data are turned off, they are omitted from the
        bar. If all the stats are missing, then an empty
        string is returned."""

        stats = (self.time_str, self.coord_str, self.percentage_str)

        return "".join(stat + " " for stat in stats if stat).strip()

    @property
    def bar_exists(self):

        """Returns whether the bar of stats above the map
        is shown or not. The bar is omitted from the GUI
        if the time, coords, and percentage are not displayed."""

        return any(
            (self.display_percentage,
             self.display_coords,
             self.platformer.timelimit != float("inf")
             )
        )

    @property
    def window_height(self):

        """Returns the total number of newlines taken up by the
        platformer GUI in the terminal, from the top all the way down
        (excluding the input arrow)."""

        screen_len = self.platformer.SCREEN_LEN
        y_len = screen_len if screen_len > 0 else self.platformer.maps.game.y_len

        map_len = y_len + 2

        return map_len + self.text_length + self.bar_exists

    @property
    def screen_slice_x(self) -> None:

        """Based on the CAMERA.x_len class variable, this function
        creates a slice object that creates a camera effect
        with the player at the center. Specifically, it creates a
        slice for the x-axis, bounding it so that the slice does
        not exceed the bounds of the map. If CAMERA.x_len is
        None, then an empty slice is returned and the camera does
        not track along the x-axis.
        """

        x_len = self.platformer.CAMERA.x_len

        if x_len is None:
            return slice(None, None, None)

        x = self.platformer.frame.coords.x

        bottom = max(0, x - (x_len // 2))

        top = min(
            self.platformer.maps.game.x_len - 1,
            bottom + x_len
        )

        if top == self.platformer.maps.game.x_len - 1:
            bottom = top - x_len

        return slice(bottom, top, None)

    @property
    def screen_slice_y(self) -> None:

        """Based on the CAMERA.y_len class variable, this function
        creates a slice object that creates a camera effect
        with the player at the center. Specifically, it creates a
        slice for the y-axis, bounding it so that the slice does
        not exceed the bounds of the map. If CAMERA.y_len is
        None, then an empty slice is returned and the camera does
        not track along the y-axis.
        """

        y_len = self.platformer.CAMERA.y_len

        if y_len is None:
            return slice(None, None, None)

        y = self.platformer.frame.coords.y

        bottom = max(0, y - (y_len // 2))

        top = min(
            self.platformer.maps.game.y_len - 1,
            bottom + y_len
        )

        if top == self.platformer.maps.game.y_len - 1:
            bottom = top - y_len

        return slice(bottom, top, None)

    def _prefix(self, header: str, prefix: str):

        """Attaches a prefix of length 1 to a header. This is shown in the GUI
        in game. For example, the player's icon is typically used as a prefix."""

        if len(prefix) != 1:
            raise ValueError("Expected string of length 1")

        return f"{prefix} | {header}"

    def print_desc(self):

        """Prints the description of a level, which can be shown
        by typing 'desc' or pressing [e]. It formats the description
        into a box with the same height as the platformer,
        while also displaying metadata such as the author
        and date of creation if the 'meta' parameter is set to True."""

        x_len = self.platformer.maps.game.x_len

        # Do not show anything if description is empty
        if self.platformer.desc:
            desc = f"[{self.platformer.title.upper()}] Description: {self.platformer.desc}"
        else:
            desc = ""

        lines = [f"| {line:<{x_len-2}} |" for line in wrap(desc, width=x_len-2)]

        # List of lines up to the end of the description
        display = ["~"*(x_len+2)] + lines

        # Lines for metadata
        r = 2 * self.platformer.meta

        # Number of blank lines to fill
        remainder = (self.window_height - r - 1) - len(display)
        display.extend([f"| {' '*(x_len-2)} |" for i in range(remainder)])

        # Append metadata lines
        if self.platformer.meta:
            author = f"[Created by: {self.platformer.author}]"
            date = f"[Date of creation: {self.platformer.date}]"
            display.append(f"| {author:<{x_len-2}} |")
            display.append(f"| {date:<{x_len-2}} |")

        display.append("~" * (x_len+2))

        stdout.write("\n".join(display) + "\n")

    def print_map(self, game_map: GameMap | None=None):

        """Prints the game map. It also prints the
        default map depending on the debug argument
        given to the platformer. If the debug argument
        is HORIZONTAL, the default map is printed
        to the right of the game map. Else,
        it is printed below."""

        if game_map is None:
            game_map = self.platformer.maps.game

        slice_tuple = (self.screen_slice_x, self.screen_slice_y)

        game_map = game_map[slice_tuple]

        map_str = str(game_map)

        if self.platformer.debug != Debug.NONE:

            default_map = self.platformer.maps.default[slice_tuple]

            default_str = str(default_map)

            if self.platformer.debug == Debug.HORIZONTAL:
                new_str = []
                for l1, l2 in zip(map_str.splitlines(), default_str.splitlines()):
                    new_str.append(f"{l1}{l2[1:]}")
                map_str = "\n".join(new_str) + "\n"

            elif self.platformer.debug == Debug.VERTICAL:
                map_str += default_str

        stdout.write(map_str)

    def print_header(self, header: str | None=None) -> None:

        """Prints the header above the game map.
        There is an option to provide a custom string,
        which is used in the platformer. It will print
        the info message if the player is currently
        on an info block. Else, it will print the title
        and shortened description."""

        # Makes the following code more concise
        def write(header: str, prefix: str) -> None:
            stdout.write(self.fill(self._prefix(header, prefix)) + "\n")

        x_len = self.platformer.maps.game.x_len

        if header is not None:
            write(str(header), self.platformer.icon)

        elif self.platformer.frame.coords in self.platformer.info_msgs:
            info_msg = self.platformer.info_msgs[self.platformer.frame.coords]

            write(str(info_msg), "?")

        else:

            title_str = shorten(
                self.platformer.title.upper(),
                width=x_len // 3, placeholder="..."
            )

            desc_str = " " + self.platformer.desc if self.display_desc else ""

            header = shorten(
                f"[{title_str!s}]{desc_str!s}",
                width=x_len, placeholder="..."
            )

            write(header, self.platformer.icon)

    def render(self, game_map: GameMap | None=None, header: str=None, pad: bool=False):

        """Renders the platformer onto the terminal. There are three
        optional arguments: a custom game map, a custom header, and 'pad'.
        The custom game map and header are used to temporarily modify
        the GUI of the game, such as when you are launching or teleporting.
        The 'pad' argument is used in special situations when we temporarily
        get rid of the information bar on the screen. To keep the screen
        stable, we instead write a newline.

        The GUI for the platformer consists of a header,
        followed by a bar containing the time limit, coordinates,
        and percentage. Finally, it prints out the game map."""

        self.print_header(header)

        stdout.flush()

        if self.bar_exists:
            stdout.write(self.stats_bar + "\n")
        elif pad: # If the bar is not shown, write a newline.
            stdout.write("\n")

        stdout.flush()

        self.print_map(game_map)

        stdout.flush()

    def game_over(self, win_condition: WinCondition):

        """Takes in a win condition and prints the
        string representation before waiting for two
        seconds. This happens when the player has
        either won or lost, and it is effectively a
        'game over' function."""

        stdout.write(win_condition.win_repr + "\n")
        sleep(2)

class Debug(Enum):

    NONE = 0
    HORIZONTAL = auto()
    VERTICAL = auto()

class Platformer:

    """The main class of the ascii-ascent project. This takes
    in a LevelData object and allows the user to play it
    through the terminal.

    Besides level data, the Platformer takes in several other
    keyword arguments:
    - The player icon (set to 'O' on default)
    - An optional debug mode, which displays the map
    without the player's icon (known as the default map)
    - A parameter controlling whether metadata such
    as the author and date of creation are shown
    to the user
    - Settings controlling whether the description,
    coordinates, or percentage are shown above the game map.
    """

    CAMERA = Camera(None, None)

    __slots__ = (

        # Level Data Object
        "_level_data",

        # Level Data (expanded out for easy access)
        "maps",
        "desc",
        "timelimit",
        "title",
        "info_msgs",
        "author",
        "date",

        # Keyword Parameters
        "icon",
        "debug",
        "meta",
        "display_desc",
        "display_coords",
        "display_percentage",

        # Derived Data
        "start",

        # Current Data
        "frame",

        # Collection Related
        "coin_counter",

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
        "checker",
        # "log_map", # `Log

    )

    def __init__(self,
                 level_data: LevelData, /, *,
                 icon: str="O",
                 debug: Debug=Debug.NONE,
                 meta: bool=True,
                 display_desc: bool=True,
                 display_coords: bool=False,
                 display_percentage: bool=True
                 ) -> None:

        self._level_data = level_data.copy()

        if self._level_data == LevelData.NULL:
            return
        elif not self._level_data:
            raise ValueError(f"Corrupted LevelData object {self}")

        title, author, date, desc, game_map, time, info_msgs, _ = level_data

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

        self.coin_counter = CoinCounter(self.maps.game.count("@"))

        self.keys = Keys() # lowercase k, UPPERCASE K

        self.locks = Locks(game_map)
        self._progress_locks() # Handles NOT locks, etc.

        self.jumps = 0
        self.start_time = None

        self.hidden = False

        self.portals = Portals(game_map)

        # Spaces moved:
        # - on x when not sprinting (sx)
        # - on x when sprinting (fx)

        # - on y currently (y)
        # - on y when sprinting (fy)

        self.move = MovementParameters()

        self.info_msgs = InfoMsgs.from_memory_efficient(
            self._level_data.info, self.maps.default
        )

        self.down = True

        # Whether the gravity has been flipped during this tick
        self.gravity_changed = False

        # Whether the player has been teleported during this tick
        self.teleported = False

        # Both of these variables prevent a player from being flipped/teleported
        # more than once per tick

        self.display_desc = display_desc
        self.display_coords = display_coords
        self.display_percentage = display_percentage

        self.renderer = Renderer(self)
        self.checker = WinDeathChecker(self)

    @property
    def gravity(self) -> int:
        return 1 if self.down else -1

    @gravity.setter
    def gravity(self, val: int) -> None:

        if abs(val) == 1:
            self.down = bool(val + 1)

    @property
    def elapsed(self) -> float:

        if self.start_time is None:
            return -1.0

        return perf_counter() - self.start_time

    @property
    def time_surpassed(self) -> bool:

        return self.elapsed > self.timelimit

    @property
    def death_status(self) -> tuple[Status, int]:

        return Status(Result.NONE, float("inf")), self.jumps

    def _new_move(self, move: str) -> str:

        """If gravity is flipped, the controls for the player
        need to be adjusted. For example, pressing 'sd' will
        now act like jumping to the right, but upside down.
        This function modifies the player's move so that it
        is consistent with normal gravity."""

        if self.down:
            return move
        else:

            table = str.maketrans({"w": "s", "s": "w"})
            move = move.translate(table)
            return move

    def _check_item_collection(self, coords: Coordinates) -> None:

        """
        A function that runs during every tick of the player's movement/path,
        such as in self._new_position_helper(), self._apply_gravity(), etc.
        This function checks whether an item is currently at the player's
        coordinate, and if so, collects it. For example, the function
        collects coins and keys, as well as hole blocks that get rid
        of keys. It also hides or unhides the character. This function
        does not return anything, as it only modifies the game state."""

        # self.log_map[coords] = self.icon # `Log

        collected = False

        i = self.maps.default[coords]

        match i:
            case "@":
                self.coin_counter.update()
                collected = True
            case "k" | "K":
                self.keys.set_char(i, True)
                collected = True
            case "h" | "H":
                self.keys.set_char("k" if i == "h" else "K", False)
            case "/":
                self.hidden = True
            case "\\":
                self.hidden = False

        # Removes coins or keys from the map
        if collected:
            self.maps.clear(coords)

        # Updates locks now that the number of keys collected has changed
        if i in KEYS:
            self._progress_locks()

    def _affected_frame(self, coords: C) -> tuple[ExecutionFrame, bool]:

        """Performs an operation on the player's frame in special cases,
        returning this new modified frame.
        The list of things _affected_frame actually does is:
        - Marks the player as having won if they are currently at a finish
        block
        - Flips the player's gravity and returns the gravity-affected frame
        if the gravity has not been flipped before. *
        - Teleports the player if they are in a portal and have not been
        teleported before.
        - Launches the player if they are at a launcher block.
        - Else, it just returns the player's frame.

        The function also returns a boolean on whether the frame was modified by the function.

        * This ensures that the player doesn't flip gravity two times during movement, preventing
        infinite loops.
        """

        if self.maps.default[coords] == "F":
            return ExecutionFrame(AliveCode.WON, coords), True

        if (
            self.gravity_changed is False and
            self.maps.default[coords] in GRAVITY
        ):

            self.gravity_changed = True

            return (
                self._flip_gravity(
                ExecutionFrame(AliveCode.ALIVE, coords),
                self.maps.default[coords]
                                       ),
                    True
            )

        if self.maps.default[coords] in TELEPORT and not self.teleported:

            self.teleported = True
            return self._teleport(coords), True

        if self.maps.default[coords] == "$":

            return self._launch(coords), True

        return ExecutionFrame(AliveCode.ALIVE, coords), False

    def _apply_gravity(self, frame: ExecutionFrame) -> ExecutionFrame:

        """Runs a loop on the player's coordinates if the player is in
        midair, bringing the player down to the ground. It decreases
        the y-value by the gravity until the player encounters
        a hard object (in NOT_PASSABLE) below them, where the loop then terminates.
        It also runs _check_item_collection and _affected_frame. What this means
        is that there are often recursive calls of _apply_gravity within itself,
        such as when gravity gets flipped in midair. This function also returns
        an ExecutionFrame."""

        # Variables used in the loop
        new = frame.coords.copy()
        below = new.adj("s", self.gravity)

        current_chr = self.maps.game[new]
        chr_below = self.maps.game[below]

        # Player won or lost - do not apply gravity
        if not frame.alive.is_alive():
            return frame

        # Check item collection
        self._check_item_collection(new)

        # Retrieve modified frame if special character was encountered
        new_frame, changed = self._affected_frame(new)

        if changed:
            return new_frame

        # Out of bounds returns NaC, which is in NOT_PASSABLE, so falling off
        # the edge of the map terminates here without a separate bounds check.
        while (chr_below not in NOT_PASSABLE and
               # guards the rare "alive but embedded in a solid" case
               # (e.g. swept into by an arrow platform)
               current_chr not in NOT_PASSABLE):

            new.y -= self.gravity

            # Update loop variables
            below = new.adj("s", self.gravity)

            current_chr, chr_below = self.maps.game[new], self.maps.game[below]

            if (frame := self._enter(new)) is not None:
                return frame

        return ExecutionFrame(AliveCode.ALIVE, new)

    def _enter(self, cell: C) -> ExecutionFrame | None:

        """This function is the subroutine that runs for every cell the player
        enters during movement. It checks if the player is in a spike,
        collecting something, or in a special block, and returns a frame
        to be passed to the outer function for early exit. Else, it will
        return None and the outer function will continue as normal.
        Specifically, this function is used in _apply_gravity and
        _new_position_helper."""

        if self.maps.game[cell] == "x":
            return ExecutionFrame(AliveCode.DEAD, cell)

        self._check_item_collection(cell)

        new_frame, changed = self._affected_frame(cell)
        if changed:
            return new_frame

    def _new_position_helper(self, move: str, player_coords: C) -> ExecutionFrame:

        """The main movement engine of the Platformer class, along with
        _apply_gravity. It parses the user's input and moves the player
        up vertically before moving them to the left or right based
        on what move they entered. It also runs _check_item_collection
        and _affected_frame along every tick of their movement trajectory,
        so that blocks can affect the character within midair. The completed
        trajectory of the player (besides special cases handled by
        _affected_frame) involves applying gravity after the initial arc
        of the player is computed in this function.

        Something worth noticing is that _new_position_helper never checks
        the first cell. However, it always checks the last cell."""

        move = self._new_move(move)

        # New coordinates to be modified
        new = player_coords.copy().as_normal()

        # The player's original coordinates
        o = player_coords.copy().as_normal()

        # Shifts the user's coordinates down by one block
        # if their move was of the form 'sd' or 'sa'.
        # Then, the rest of the movement for these cases
        # comes from horizontal shifting.

        if len(move) == 2 and "s" in move:

            direction = "a" if "a" in move else "d"

            new.y -= self.gravity

            if self.maps.game[new] in HARD and self.maps.game[new.adj(direction, self.gravity)] in HARD:
                return ExecutionFrame(AliveCode.ALIVE, o)
            elif self.maps.game[new] not in HARD:

                if (frame := self._enter(new)) is not None:
                    return frame

            # In this case, we are now in the ground, but there
            # is a transparent block right next to us.
            # This will be settled in the main match statement.

        match move:

            case "w": # Upwards movement (by 1 or 2 blocks at most)

                current_chr = self.maps.game[o]
                chr_above = self.maps.game[new.adj("w", self.gravity)]

                # Moving up into a ladder (or in a ladder), move up once and stop.
                if "_" in {current_chr, chr_above}:

                    new.y += self.gravity

                    if (frame := self._enter(new)) is not None:
                        return frame

                    return ExecutionFrame(AliveCode.ALIVE, new)

                # Move up by move.Y while the block above is not hard
                # (see Y constant defined at top of file)

                while (
                        self.maps.game[new.adj("w", self.gravity)] not in HARD and
                        abs((new - o).y) < self.move.Y
                ):

                    new.y += self.gravity

                    if (frame := self._enter(new)) is not None:
                        return frame

            case "s":

                # Move down
                if self.maps.game[new.adj("s", self.gravity)] not in HARD:
                    new.y -= self.gravity

                    if (frame := self._enter(new)) is not None:
                        return frame

            case "a":

                left = new.adj("a", self.gravity)

                # Move left by SLOW_X while the block to the left is not hard
                # (see SLOW_X constant defined at the top of the file)

                while (
                        self.maps.game[left] not in HARD
                        and abs((new - o).x) < SLOW_X
                ):

                    new.x -= 1

                    if (frame := self._enter(new)) is not None:
                        return frame

                    left = new.adj("a", self.gravity)

            case "d":

                right = new.adj("d", self.gravity)

                # Move right by SLOW_X while the block to the right is not hard
                # (see SLOW_X constant defined at the top of the file)

                while (
                        self.maps.game[right] not in HARD
                        and abs((new - o).x) < SLOW_X
                ):

                    new.x += 1

                    if (frame := self._enter(new)) is not None:
                        return frame

                    right = new.adj("d", self.gravity)

            case "aw" | "wa":

                above = new.adj("w", self.gravity)

                # Move up by move.Y while the block above is not hard
                # (see Y constant defined at top of file)

                while (
                        self.maps.game[above] not in HARD
                        and abs((new - o).y) < self.move.Y
                ):

                    new.y += self.gravity
                    above.y += self.gravity

                    if (frame := self._enter(new)) is not None:
                        return frame

                left = new.adj("a", self.gravity)

                o = new.copy()

                # Move left by FAST_X while the block to the left is not hard
                # (see FAST_X constant defined at the top of the file)

                while (
                        self.maps.game[left] not in HARD
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    # In the case solid ground appears below the player,
                    # the player has landed on something. As such, the
                    # player will halt instead of overshooting and continuing
                    # to move horizontally.

                    if self.maps.game[new.adj("s", self.gravity)] in HARD and self.move.Y > 0:
                        break

                    new.x -= 1
                    left.x -= 1

                    if (frame := self._enter(new)) is not None:
                        return frame

            case "dw" | "wd":

                above = new.adj("w", self.gravity)

                # Move up by move.Y while the block above is not hard
                # (see Y constant defined at top of file)

                while (
                        self.maps.game[above] not in HARD
                        and abs((new - o).y) < self.move.Y
                ):

                    new.y += self.gravity
                    above.y += self.gravity

                    if (frame := self._enter(new)) is not None:
                        return frame

                right = new.adj("d", self.gravity)

                o = new.copy()

                # Move right by FAST_X while the block to the right is not hard
                # (see FAST_X constant defined at the top of the file)

                while (
                        self.maps.game[right] not in HARD
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    # In the case solid ground appears below the player,
                    # the player has landed on something. As such, the
                    # player will halt instead of overshooting and continuing
                    # to move horizontally.

                    if self.maps.game[new.adj("s", self.gravity)] in HARD and self.move.Y > 0:
                        break

                    new.x += 1
                    right.x += 1

                    if (frame := self._enter(new)) is not None:
                        return frame

            # Note that vertical movement downward for cases 'as'
            # and 'ds' were covered at the beginning of this method.
            # This allows us to consolidate "as" and "aa",
            # as well as "ds" and "dd" as both now only cover
            # fast horizontal movement.

            case "as" | "sa" | "aa" | "a'" | "'a'":

                left = new.adj("a", self.gravity)

                # Move left by move.FAST_X while the block to the left is not hard
                # (see FAST_X constant defined at the top of the file)

                while (
                        self.maps.game[left] not in HARD
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    new.x -= 1

                    if (frame := self._enter(new)) is not None:
                        return frame

                    left = new.adj("a", self.gravity)

            case "ds" | "sd" | "dd" | "d'" | "'d'":

                right = new.adj("d", self.gravity)

                # Move right by move.FAST_X while the block to the right is not hard
                # (see FAST_X constant defined at the top of the file)

                while (
                        self.maps.game[right] not in HARD
                        and abs((new - o).x) < self.move.FAST_X
                ):

                    new.x += 1

                    if (frame := self._enter(new)) is not None:
                        return frame

                    right = new.adj("d", self.gravity)

        # Return the new coordinates
        return ExecutionFrame(AliveCode.ALIVE, new)

    @staticmethod
    def _gravity_affected(func) -> Callable:

        """This convenient decorator essentially applies gravity to the result of a function.
        This is really useful because often after an operation on the player's coordinates,
        we need to bring the user to a stable state and apply gravity before we use the
        result of this function.

        To use _gravity_affected, the function being decorated must return an
        ExecutionFrame, which is validated below. Gravity is then applied to the resulting
        frame.

        Another implementation detail is that the frame returned by a decorated function
        always uses normal coordinates."""

        @wraps(func)
        def wrapper(self: Platformer, *args, **kwargs):

            frame = func(self, *args, **kwargs)

            if not isinstance(frame, ExecutionFrame):
                raise TypeError(
                    f"Function {func.__name__} did not return an ExecutionFrame object."
                )

            frame.normalize() # To apply gravity

            frame = self._apply_gravity(frame)

            # Convert the frame to normal coordinates (just to be sure)
            frame.normalize()

            return frame

        return wrapper

    @_gravity_affected
    def _check_countdown_collision(self, frame: ExecutionFrame) -> ExecutionFrame:

        """(For context, this function runs AFTER the countdown
        blocks are updated.)

        This function marks a player as dead if they are in a countdown block.
        It will also apply gravity onto the player if they have landed on a countdown
        block that has since disappeared."""

        alive = frame.alive

        if self.maps.default[frame.coords] in COUNTDOWN:

            alive = AliveCode.DEAD

        return ExecutionFrame(alive, frame.coords)

    def _progress_countdown(self, frame: ExecutionFrame) -> ExecutionFrame:

        """Performs all operations related to countdown blocks, namely
        updating the countdown blocks on the map and updating
        the player state."""

        self.maps.update_countdown_blocks()
        frame = self._check_countdown_collision(frame)

        return frame

    def _check_platform_collision(self, frame: ExecutionFrame):

        """This function handles the complex interaction between the player's
        coordinates and the platforms. It handles the cases for
        horizontal arrows, 'conveying' the player to the right place.
        For down arrows, it takes the player down one character.

        For up arrows, the behavior is more complicated. If the player crashes
        into the ceiling or into a hard block, they are dead. (These are handled as
        separate cases due to visual differences; read the comments left
        for this case.) Else, the player moves up as usual."""

        coords = frame.coords.as_normal()
        alive_code = AliveCode.ALIVE

        # Makes the following code more concise
        adj = partial(coords.adj, g=self.gravity)

        # A bunch of characters to make comparisons cleaner.
        current = self.maps.default[coords]
        char_above = self.maps.default[adj("w")]
        char_under = self.maps.game[adj("s")]
        char_dunder = self.maps.game[adj("ss")]
        char_left = self.maps.default[adj("a")]
        char_right = self.maps.default[adj("d")]
        char_s_left = self.maps.game[adj("sa")] # Character to the southwest
        char_s_right = self.maps.game[adj("sd")] # Character to the southeast

        # A bunch of sets of characters to make comparisons cleaner.
        ARROWS, BELTS = MapCharset("V^<>"), MapCharset("|-")
        HARD_NO_ARROWS = (HARD - ARROWS)

        # Down and up arrows relative to gravity
        down_arrow = "V" if self.down else "^"
        up_arrow = "^" if self.down else "V"

        # moved is True when a platform moved the player, requiring another
        # application of gravity and setting gravity_changed back to False.
        moved = True

        match char_under:

            # The ternary statements in this piece of code are to judge
            # whether a belt will continue in a given direction or turn around.

            case "<":
                if char_s_left in HORIZONTAL and char_left not in HARD_NO_ARROWS:
                    coords.x -= 1
                elif char_s_left not in HORIZONTAL and char_right not in HARD_NO_ARROWS:
                    coords.x += 1
            case ">":
                if char_s_right in HORIZONTAL and char_right not in HARD_NO_ARROWS:
                    coords.x += 1
                elif char_s_right not in HORIZONTAL and char_left not in HARD_NO_ARROWS:
                    coords.x -= 1
            case i if i == down_arrow:
                coords.y -= self.gravity if char_dunder in VERTICAL else -self.gravity

            case i if i == up_arrow and current != "_":

                # Reached the top of the platform belt.

                if current in TRANSPARENT:
                    coords.y -= self.gravity

                # All other conditions from here mean the icon
                # is still moving upward.

                # The following two cases are really the same;
                # they differ only in visual presentation.
                # When a player crashes into the ceiling,
                # the visual effect is the player being crushed into
                # the ceiling or being moved "outside" the map.
                # When a player crashes into a block,
                # the player can still be seen and is not hidden.

                # NOTE: these cases could be unified if we accept
                # that a player's coordinates can go outside the
                # map. But this is not worth it as it is nice
                # to know for a fact that in this game,
                # a player's coordinates are in the bounds.
                # Breaking such an invariance is not a good idea.

                elif not self.maps.game._bounded(adj("w")):

                    self.maps.both[coords] = "|"
                    alive_code = AliveCode.DEAD
                    self.hidden = True

                elif char_above in HARD_NO_ARROWS:

                    coords.y += self.gravity
                    alive_code = AliveCode.DEAD

                else:

                    # Move up: upper character is not hard.
                    coords.y += self.gravity

            case _:

                # This occurs when the player is not above an arrow,
                # and as such, does not move.
                # Also, another case is where the character below is an
                # up arrow and the character that is currently in the
                # player's place is a ladder '_'.

                # This means that the platform ends at this point, but
                # the player 'sticks' or 'holds on' to the ladder.
                # This means the player does not move.

                moved = False

        if self.maps.default[coords] == "x":
            alive_code = AliveCode.DEAD

        return ExecutionFrame(alive_code, coords), moved

    def _progress_platforms(self, frame):

        """The main function that handles platform generation and
        replacement. It moves all the platforms using the
        other helper functions, moving the player with it
        if they are on top of a platform.

        This function does not use _gravity_affected, as it
        uses more precise control on gravity. If the player
        moved, we apply gravity and set gravity_changed back
        to False, allowing for flipping. Else, we
        do not allow the player to flip again."""

        frame, moved = self._check_platform_collision(frame)
        self.maps.update_platforms()

        if moved:
            self.gravity_changed = False
            frame = self._apply_gravity(frame)

        frame.normalize()
        return frame

    def _progress_locks(self) -> None:

        """After the player's keys have changed,
        _progress_locks updates the locks based
        on the new boolean values. This function is called
        in _check_item_collection() whenever a key is collected
        (or lost)."""

        for i, lock, not_lock in zip("kK", "lL", "nN"):

            self.locks.edit(lock, self.keys.get_char(i))
            self.locks.edit(not_lock, not self.keys.get_char(i))

        self.locks.edit("A", all(self.keys))
        self.locks.edit("X", self.keys.k != self.keys.K)

        self.maps.update_locks(self.locks)

    @_gravity_affected
    def _launch(self, launch_point: C) -> ExecutionFrame:

        """Allows the player to launch from a given starting point. The player is only
        able to launch within a radius of 6 characters. They can move their target location
        using standard [w/a/s/d] controls. Then, the player presses [x] to launch.

        This function uses a copy of the game map to create its own GUI for launch mode. The
        coordinates that the player selects are always proven to be a valid trajectory,
        so the display simply traces the trajectory.

        Another detail is that while launching, the gravity_changed variable
        is reset. Since launching is a stable state for the player, we can allow
        the player to flip again after a launch. We do something similar for teleports.

        The display_coords and display_percentage flags are turned off during launching,
        since the coordinates and percentage of the launch point do not represent where
        the player actually is launching. Since this might make the bar disappear,
        we use the pad argument in Renderer.render to pad the bar.

        Launching is handled cleverly, as this function does not compute the trajectory
        of the player itself. Instead, it temporarily changes the game's movement parameters
        and handles the trajectory as a big jump from the launch point. In other words,
        launches and jumps work in the exact same way."""

        # Save old attribute values, we will temporarily replace them.
        display_coords, display_percentage = self.display_coords, self.display_percentage

        pad = self.renderer.bar_exists

        self.display_coords = False
        self.display_percentage = False

        # Allows us to chain gravity flips and launches / teleports.
        self.gravity_changed = False
        self.teleported = False

        # The radii for the area that the player can launch in
        # (actually, the launch area is a square rather than a circle)

        x_radius = 6
        y_radius = 6

        # The maximum indices for x and y.
        top_x = self.maps.game.x_len - 1
        top_y = self.maps.game.y_len - 1

        # Bounds for moving around.
        lower_x = max(launch_point.x - x_radius, 0)
        upper_x = min(launch_point.x + x_radius, top_x)

        lower_y = launch_point.y

        # Clamp (y + self.gravity * y_radius) to a valid y-level.
        upper_y = max(min(launch_point.y + self.gravity*y_radius, top_y), 0)

        if not self.down:
            lower_y, upper_y = upper_y, lower_y # We are launching downwards in this case, not upwards

        # The map before launching (used for creating displays)
        original_map = self.maps.game.copy()

        # The coordinates to launch to
        target = launch_point.copy()

        INTERRUPT_ARC = TELEPORT | GRAVITY | MapCharset("x$FS")

        while True:

            # Create display with new coordinates
            display = original_map.copy()

            for i in C.arc(launch_point, target):

                # Trace out the player's trajectory.
                if original_map[i] not in INTERRUPT_ARC:
                    display[i] = "!"

            display[target] = self.icon

            clear()
            self.renderer.render(game_map=display, header="Launch!", pad=pad)

            j = IOUtils.input("Select where to launch ([wasd]/[x] to drop). ")

            undo_target = target.copy()

            match j:

                case "w":
                    target.y += 1
                case "s":
                    target.y -= 1
                case "a":
                    target.x -= 1
                case "d":
                    target.x += 1

                case "x": # Launch the player by swapping out movement parameters

                    dx, dy = abs(target - launch_point)

                    old_movement_parameters = self.move
                    self.move = MovementParameters(dx, dy)

                    launch_move = f"w{'a' if target.x < launch_point.x else 'd'}"

                    frame = self._new_position_helper(launch_move, launch_point)

                    self.move = old_movement_parameters

                    self.display_coords = display_coords
                    self.display_percentage = display_percentage

                    clear()

                    return frame

            # Bound coordinates
            target.x = max(min(target.x, upper_x), lower_x)
            target.y = max(min(target.y, upper_y), lower_y)

            # If our new coordinate does not yield a valid trajectory, we revert back to
            # what we had before.

            for i in C.arc(launch_point, target):
                if original_map[i] in HARD:
                    target = undo_target.copy()
                    break

    @_gravity_affected
    def _teleport(self, coords: C) -> ExecutionFrame:

        """Allows the player to teleport to a different location. In the case that
        the player is not in a portal, or there are no matching portals,
        _teleport does nothing. In the case that there is only one portal to map
        to, the method automatically selects the only choice and returns the
        new frame.

        Else, the player has to choose between many different possible locations. In this case,
        the program takes all the possible locations and sorts them by x-position and y-position.
        Two indices are maintained to make w/a/s/d movement feel natural in a discrete
        set of points.

        Like in _launch, display_coords and display_percentage are turned off during
        teleportation, for very similar reasons.

        When the user presses [x] to select a teleport location, an ExecutionFrame object
        is returned with the new location the user chose. Note that gravity is also
        applied to the final coordinate."""

        self.gravity_changed = False

        # Get coordinates of possible portals to teleport to
        try:
            possible_coords = self.portals[coords]
        except KeyError: # No portals to teleport to, exit
            return ExecutionFrame(AliveCode.ALIVE, coords)

        num_found = len(possible_coords)

        if num_found == 1: # Only one possible place to teleport
            return ExecutionFrame(AliveCode.ALIVE, possible_coords[0])
        else: # Run GUI

            display_coords, display_percentage = self.display_coords, self.display_percentage

            pad = self.renderer.bar_exists

            self.display_coords = False
            self.display_percentage = False

            # Sort coordinates by x and y. This makes navigating
            # coordinates more intuitive with w/a/s/d controls.

            possible_coords_x = sorted(possible_coords,
                                       key=lambda c: (c.x, c.y))
            possible_coords_y = sorted(possible_coords,
                                       key=lambda c: (c.y, c.x))

            original_map = self.maps.game.copy()

            x_index = 0
            y_index = possible_coords_y.index(possible_coords_x[x_index])

            while True:

                display = original_map.copy()

                portal_coord = possible_coords_x[x_index]

                for coord in portal_coord.adjs("w", "a", "s", "d"):
                    display[coord] = "!"

                clear()
                self.renderer.render(game_map=display, header="Teleport!", pad=pad)

                j = IOUtils.input("Select where to teleport ([wasd]/[x] to select). ")

                match j:

                    # Note that we use the y-sorted list when navigating
                    # horizontally, and vice versa.
                    # This is because the second sort key in lexicographical sort
                    # is the direction that points head in locally.
                    # So, in the y-sorted list, locally the coordinates are moving
                    # in the x-direction, and vice versa.

                    case "a" | "d":

                        y_index += 1 if j == "d" else -1
                        y_index %= num_found

                        x_index = possible_coords_x.index(possible_coords_y[y_index])
                        x_index %= num_found

                    case "w" | "s":

                        x_index += 1 if j == "w" else -1
                        x_index %= num_found

                        y_index = possible_coords_y.index(possible_coords_x[x_index])
                        y_index %= num_found

                    case "x":

                        self.display_coords = display_coords
                        self.display_percentage = display_percentage

                        clear()
                        return ExecutionFrame(AliveCode.ALIVE, portal_coord)

    def _new_position(self, move: str) -> ExecutionFrame:

        """Finds the new position for the player, given their current coordinates
        and the move they made. Firstly, we run _new_position_helper to get
        the initial frame based on the player's current coordinates, running
        the move they made. We then apply gravity to the frame, finishing the
        movement arc."""

        return self._apply_gravity(self._new_position_helper(move, self.frame.coords.copy()))

    @_gravity_affected
    def _flip_gravity(self, frame, char: Literal["+", "="]):

        """Flips the current gravity and applies gravity in this new direction to a given
        frame."""

        self.down = False if char == "+" else True
        return frame

    def _progress_helper(self, move: str) -> ExecutionFrame:

        """This function computes the player's position, taking not just into account
        the move they made (like in _new_position), but the surrounding environment.
        For example, after the initial new_frame is received from _new_position(),
        we update the platforms and countdown blocks in the map. We then receive the
        player's new state after these updates. Whenever the player reaches some
        state of inertia, like after new_position or _progress_countdown, we also
        check if there are asterisk blocks underneath the player and add them to
        stepped_on."""

        self.stepped_on.clear()

        new_frame = self._new_position(move)

        if not new_frame.alive.is_alive():
            return new_frame

        # Landed on the ground: populate stepped_on
        self.stepped_on.populate(self, new_frame)

        # Map updates: platforms and countdown blocks

        new_frame = self._progress_platforms(new_frame)

        if not new_frame.alive.is_alive():
            return new_frame

        new_frame = self._progress_countdown(new_frame)

        if not new_frame.alive.is_alive():
            return new_frame

        # Landed on the ground: populate stepped_on
        self.stepped_on.populate(self, new_frame)

        return new_frame

    def _clear_items(self):

        """Clears the asterisks stepped on during the last tick from
        the map, as well as patching up the player's icon."""

        self.maps.clear_asterisks(self.stepped_on)
        self.maps.both.patch(self.frame.coords)

    def _progress(self, move: str) -> ExecutionFrame:

        """Progresses the state of the game, or moves the game forward one tick.
        It first starts out with clearing any asterisks that the player has stepped
        on during the last tick, as well as the player's icon. We retrieve the
        player's new coordinates from the move they input. We then draw the player
        at these new coordinates (unless they are hidden). We reset the gravity_changed
        and teleported attributes, and return the new frame."""

        self._clear_items()

        frame = self._progress_helper(move)

        if not self.hidden:
            self.maps.game[frame.coords] = self.icon

        self.gravity_changed = False
        self.teleported = False

        return frame

    def _prepare_game(self):

        """A function that sets up the initial state of the game
        by drawing the player's icon at the starting coordinates,
        recording the start time and clearing the screen."""

        self.maps.game[self.frame.coords] = self.icon
        self.start_time = perf_counter()
        clear()

    def _restart(self):

        """Restarts the game by resetting all the class attributes
        to their first state at initialization. This is done by literally
        calling __init__ again with the initial parameters sent to the class.
        We also re-prepare the game (see above)."""

        self.__init__(self._level_data.copy(),
                      icon=self.icon,
                      debug=self.debug,
                      meta=self.meta,
                      display_desc=self.display_desc,
                      display_coords=self.display_coords,
                      display_percentage=self.display_percentage
                      )

        self._prepare_game()

    def _pause(self, *, description: bool=False):

        """Pauses the game. There is an optional argument
        description that is used when the player wants
        to view the level description. Else, it will
        display the current game map.

        One thing to note is that the level timer stops during
        pauses. To account for this, we add the time paused
        to the start time to push the elapsed time back."""

        clear()

        pause_start_time = perf_counter()

        if description:
            self.renderer.print_desc()
        else:
            self.renderer.render(header="[||] PAUSED")

        IOUtils.input("[|>] Resume? ")

        pause_end_time = perf_counter()
        total_pause_time = pause_end_time - pause_start_time
        self.start_time += total_pause_time

        clear()

    def _parse_move(self, move: str) -> bool:

        """Takes a user's input and parses it. It detects:
        > restarting, exiting, and pausing the game
        > printing the description
        > running the user's move in-game

        In the case that the user inputted a move, the jump
        counter will also be updated.

        The function returns whether the player exited the game,
        in which case the function play() will return early.
        """

        match IOUtils.sanitized(move):

            case "exit" | "x":
                return True

            case "restart" | "r":

                clear()
                self._restart()

            case "p" | "pause":

                clear()
                self._pause()

            case "desc" | "e" if (self.desc or self.meta):

                self._pause(description=True)

            case _:

                clear()
                self.frame = self._progress(move)
                self.jumps += 1

        return False

    def play(self) -> tuple[Status, int]:

        """The main function in the Platformer class, as well as the
        only public function available for the class. It is also
        arguably the most important function in the entire program.
        It runs the Platformer game using the data given during
        initialization.

        If, during initialization, the level data passed into it
        was LevelData.NULL, the play() function will immediately
        exit. Else, it prepares the game before starting the game loop.

        Every iteration of the game loop starts out with printing the
        map to the console using the Renderer class. If the player
        is dead or has won, it will display a message and exit the game.
        Else, the program collects the player's input and parses it
        (see _parse_move above). If the player types in 'exit' or 'x',
        the program will exit early.
        """

        # Allows for an edge case when the user is selecting
        # a level through a pagination GUI.
        # If the player exits the GUI, LevelData.NULL is
        # returned for consistency. When this level is played,
        # nothing happens.

        if self._level_data == LevelData.NULL:
            return self.death_status

        self._prepare_game()

        while True: # Main game loop

            self.renderer.render()

            data = self.checker.get_return_value()

            if isinstance(data, WinCondition):
                self.renderer.game_over(data)
                return data.status, data.jumps

            exited = self._parse_move(IOUtils.input("-> "))

            # logger.debug(self.title + "\n" + str(self.log_map) + "\n") # `Log
            # self.log_map = self.maps.default.copy() # `Log

            # Exited the game
            if exited:
                return self.death_status

################################################################################

class Tower(Platformer):

    """A class for the final level, which is way taller
    (it's a tower, obviously) and also implements camera
    tracking along the y-axis to keep the 63 x 12 screen
    dimensions. This mode can be used for any levels that
    require vertical camera tracking."""

    CAMERA = Camera(None, Constants.Y_LEN)

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
            self.e.locks = Locks(new_map)
            self.e.portals = Portals(new_map)

    def __enter__(self):

        self.e.frame = ExecutionFrame(AliveCode.ALIVE, C(0, 0))

        self.e.keys = Keys()

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
                 display_coords: bool=False, display_percentage: bool=True):

        self.parameters = parameters

        self.icon = icon
        self.debug = debug
        self.display_coords = display_coords
        self.display_percentage = display_percentage

        if _level_data is None:

            with MapGenerator(self, debug=False) as gen:
                data = gen.generate_map(speed=0.15)

        else:
            data = _level_data.copy()

        super().__init__(data, icon=icon, debug=debug, meta=False,
                         display_desc=False, display_coords=display_coords,
                         display_percentage=display_percentage)

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
