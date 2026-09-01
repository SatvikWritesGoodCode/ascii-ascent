from __future__ import annotations

from clear import clear
from time import sleep
from random import random, choices, shuffle, sample
from textwrap import shorten
from typing import Iterator, TypeVar, Literal
from dataclasses import dataclass, field
from enum import Enum, auto

from math import floor, sin, cos, radians
from sys import stdout
from itertools import batched, chain
from textwrap import wrap
from maps import LevelData, LevelDatabase, Constants

"""<utils.py> A module that contains:
- IOUtils
- StringUtils
- InfoUtils
- EnterExitUtils
- LoadUtils
- PaginateUtils

which are 'submodules' that contain useful helper
functions.

This module also contains some other miscellaneous classes like
Achievements and PerlinNoise."""

class IOUtils:

    """A class that has to do with input and output
    (mostly input)."""

    __slots__ = ()

    class Response(Enum):

        """An enum that has to do with whether a string
        means 'yes' or 'no,' used in validation.'"""

        YES = 1
        NO = auto()
        UNKNOWN = auto()

    @staticmethod
    def sanitized(string: str, /):

        """Gets rid of leading and trailing whitespace,
        as well as making the string lowercase and
        normalizing non-ASCII characters."""

        return string.strip().casefold()

    @staticmethod
    def input(prompt: str="", /, *, sanitize: bool=False):

        """An issue with the Khan Academy terminal is that
        sometimes, after an input call, the text jitters.
        This can be (mostly) fixed using this function,
        which first writes the prompt to the terminal separately
        and then gets the input. An optional parameter,
        sanitize, can also be used to automatically sanitize
        the input."""

        stdout.write(prompt)

        x = input()
        return IOUtils.sanitized(x) if sanitize else x

    @staticmethod
    def validate(user_input: str, /) -> Response:

        """A function that figures out whether a string
        is saying 'yes' or 'no.' Uses the IOUtils.Response
        enum. This function looks at the first character
        of a string; if it is 'y,' it is saying yes,
        if it is 'n,' then it is saying no.'"""

        if user_input:
            char = IOUtils.sanitized(user_input)[0]
            if char == "y":
                return IOUtils.Response.YES
            elif char == "n":
                return IOUtils.Response.NO

        return IOUtils.Response.UNKNOWN

    @staticmethod
    def get_validation(prompt: str, /) -> Response:

        """Gets input from the user and directly
        sends it into IOUtils.validate."""

        user_input = IOUtils.input(prompt)
        return IOUtils.validate(user_input)

class StringUtils:

    """A class that helps format strings. This module powers almost
    all string formatting and GUI design across the entire game."""

    __slots__ = ()

    @staticmethod
    def format_columns(list_str: list[str], /, *, cols: int=3,
                       width=Constants.X_LEN) -> None:

        """This function takes in a list of strings, as well
        as a number of columns and a width, and formats
        the list of strings into columns."""

        batches = batched(list_str, cols)
        output = []

        col_width = width // cols
        for i in batches:

            row = "".join(x.ljust(col_width) for x in i)
            output.append(row.ljust(width))

        return "\n".join(output)

    @staticmethod
    def fast_distribute(list_str: list[str], /, *, width=Constants.X_LEN):

        """Distributes a list of characters evenly across a width."""

        if not list_str:
            return " " * width

        n = len(list_str[0])

        if any(len(s) - n for s in list_str):
            raise ValueError(
                "Can only take in list of strings with all equal lengths"
            )

        num_elements = width // (n + 1)
        result = " ".join(list_str[:num_elements]).ljust(width)

        if len(result) > width:
            result = result[:width - 3] + "..."

        return result

    @staticmethod
    def distribute(list_str: list[str], /, *, width=Constants.X_LEN):

        """Distributes a list of strings evenly across a width.
        Note that this code isn't very reliable."""

        if not list_str:
            return " " * width

        n = len(list_str)

        # Width without separating spaces is divided
        p_width = (width - (n - 1)) // n

        aux = [len(string) - p_width for string in list_str]

        debt, widths = 0, list()

        # Will only compensate starting at the second element
        # since there is no debt to compensate for yet

        for ind in range(n):

            a = aux[ind]
            if a > 0:
                debt += a
                widths.append(p_width + a)
            elif a == 0:
                widths.append(p_width)
            elif a < 0:
                b = min(abs(a), debt)
                debt -= b
                widths.append(p_width - b)

        result = " ".join(
            string.ljust(w) for string, w in zip(list_str, widths)
        )

        if len(result) > width:
            return result[:width - 3] + "..."

        return result.ljust(width)

    @staticmethod
    def list_box(list_str: list[str], /, *, subs: dict[int, str]=None):

        """Formats a list of strings into a box. A width is not specified; the
        function uses the length of the longest string as the width.
        An optional subs argument is provided, which allows suffixes
        to be flexibly placed onto different strings in the list."""

        if subs is None:
            subs = {}

        new_list = []

        max_width = max(len(string) for string in list_str)
        side = "~"*(max_width + 4)

        new_list.append(side)
        new_list.extend([f"| {string:<{max_width}} |" for string in list_str])
        new_list.append(side)

        for index, sub in subs.items():

            new_list[index+1] += f" {sub}"

        return "\n".join(new_list)

    @staticmethod
    def text_box(string: str, /, *, width: int=Constants.X_LEN,
                 newline: bool=True):

        """Fits a string of text inside a box with a given width.
        It does not format the string into bullets, instead treating
        the string as one whole piece of text and putting it inside a
        box. An optional newline parameter, set as True on default,
        controls whether a newline is appended to the end of the
        string."""

        lines = wrap(string.replace("\n", ""), width=width-2)

        lines = [f"| {line:<{width-2}} |" for line in lines]

        display = ["~"*(width+2)]
        display.extend(lines)

        display.append("~" * (width+2))

        return "\n".join(display) + ("\n" if newline else "")

    @staticmethod
    def bullet_box(list_str: list[str], /, *, width=Constants.X_LEN,
                   newline: bool=True):

        """Takes a list of strings and formats them as bullets inside a box
        with a given width. An optional newline parameter, set as True on
        default, controls whether a newline is appended to the end of the
        string."""

        new_list = [
            wrap(
                string.replace("\n", ""),
                width=(width - 2),
                initial_indent="- ",
                subsequent_indent="  "
            ) for string in list_str
        ]

        result = ["~" * (width + 2)]

        result.extend([
            f"| {line:<{width - 2}} |" for line in chain.from_iterable(
                new_list)
        ]
        )

        result.append("~" * (width + 2))

        return "\n".join(result) + ("\n" if newline else "")

    @staticmethod
    def divider(*, width: int=Constants.X_LEN):

        """Creates a divider with a given width, alternating
        between an equals sigh and a tilde.
        Example: divider(8) = '~=~=~=~='
        """

        length, extra = divmod(width, 2)
        divider = "=~"*length + "="*extra

        return divider

    @staticmethod
    def bar(list_str: list[str], /, *, width: int=Constants.X_LEN):

        """Given a list of strings, returns a string that puts
        the strings between two dividers."""

        divider = StringUtils.divider(width=width)

        new_list = []

        new_list.append(divider)
        new_list.append("\n".join(list_str))
        new_list.append(divider)

        return "\n".join(new_list)

    @staticmethod
    def _enumerated(str_list: list[str]):

        """Given a list of strings, returns an 'enumerated' list
        that prefixes each string with a number. If the string
        is 'exit', it will prefix an '[x]'; if the string is
        'info', it will prefix an '[i]'. This is mostly used
        in the menu so users can easily enter in options."""

        def new(i: int, string: str) -> str:

            if string == "Exit":
                n = "[x]"
            elif string == "Info":
                n = "[i]"
            else:
                n = f"[{i}]"

            return f"{n} {string}"

        return [new(*x) for x in enumerate(str_list, 1)]

    @staticmethod
    def menu(header: str, str_list: list[str], /, *,
             subs: dict[int, str]=None):

        """Given a header, a list of strings, and a list
        of 'subs' (which are suffixes put on the list of
        strings), returns a fully constructed menu GUI.
        This is used all across the game. The 'subs'
        parameter is given so that suffixes are completely
        flexible."""

        str_list = StringUtils._enumerated(str_list)

        menu_list = [
            header,
            StringUtils.list_box(str_list, subs=subs),
            "Select an option: "
        ]

        return "\n".join(menu_list)

@dataclass(frozen=True, slots=True)
class InfoData:

    """Stores data that is displayed as info."""

    header: str = "Info:"
    bullets: list = field(default_factory=list)
    free_text: str = ""

    def __str__(self):

        string_list = [
            self.header,
            StringUtils.bullet_box(
                self.bullets,
                width=Constants.X_LEN,
                newline=False
            )
        ]

        if self.free_text:
            string_list.append(self.free_text)

        string_list.append("Press [Enter] to continue. ")

        return "\n".join(string_list)

class InfoUtils:

    __slots__ = ()

    """Given an area of the program, gives info on how it works / should
    be used. This works similar to the help() function."""

    GENERAL = InfoData(
        header="About the Game:",
        bullets=[
            """'ASCII Ascent' is a text-based platformer that uses entirely ASCII 
characters. I am fairly sure this game is the first of its kind.""",
            """This game took an eternity to build, so please like and comment 
if you can.""",
            """Please give feedback on this game if you have any 
so I can improve it. """,
            """If you liked this game, subscribe to my subpage to support me! 
Thanks :)""",
        ],
        free_text="https://www.khanacademy.org/python-program/the-capybaras-subpage/6648125978689536"
    )

    GAME = InfoData(
        header="Help for 'Play' Mode:",
        bullets=[
            """This is the menu for climbing up the castle and 
playing the main levels.""",
            """[1] Continue Game: Plays the next level.""",
            """[2] Select Level: Select among the levels you have unlocked.""",
            """Tip: You need to collect 10 coins to unlock the Tower. If you 
cannot access the Tower, collect 10 coins and come back."""
        ]
    )

    CUSTOM = InfoData(
        header="Help for 'Custom' Mode:",
        bullets=[
            """The Custom Mode lets you view user levels as well as 
create your own!""",
            """[1] Create New Level: Sends you to the editor, where you can 
create levels. Go to 'Editor Tutorial' to learn more.""",
            """[2] Created Levels: Lets you search through your created 
levels. Once you have selected a level, you can edit that level, play it, 
delete it, or get the save string for the level.""",
            """[3] Load Save String: This feature allows you to save levels 
and share them with others. If you have a save string for a level, copy paste 
it to add it to your created levels!""",
            """[4] Public Levels: Play levels that others have created.""",
            """[5] Editor Tutorial: Teaches you how to use the editor.""",
        ]
    )

    ACCOUNT = InfoData(
        header="Help for 'View Account' Mode:",
        bullets=[
            "[1] View Stats: View your total attempts and jumps.",
            "[2] View Progress: See completion status for the main levels.",
            """[3] View Achievements: View achievements that are earned from 
playing the game. There are 16 achievements you can earn. Each achievement 
gives you 5 points, although some achievements are much harder than others.""",
            "[4]/[5]: Change Icon/Username: Username must be under 25 characters.",
            "[6] About Game: Learn more about the Platformer."
        ]
    )

    ENDLESS = InfoData(
        header="Help for 'Endless':",
        bullets=[
            """Endless Mode allows you to platform uninterrupted, 
beating harder and harder randomly generated levels while gaining points!""",
            """[1] Play: You can choose to play two different modes: Spike Trials 
and Mountain of Asterisks."""
            """Spike Trials generates terrain with spikes, whereas Mountain of 
Asterisks throws asterisk blocks into the mix as well.""",
            """[2] View Endless Mode Progress: See how far you have gotten 
in Endless Mode for both modes."""
        ]
    )

    PACKS = InfoData(
        header="Help for 'Experimental Level Packs':",
        bullets=[
            """30 new levels for you to beat, including 6 new features!""",
            """[1] Hidden Blocks: Makes the character invisible, 
so you really have to pay attention.""",
            """[2] Countdown Blocks: A block that momentarily disappears 
on a cycle.""",
            """[3] Gravity Blocks: Switches the player's gravity 
upside down or right side up.""",
            """[4] Teleporters: Teleports the icon from one location 
to another.""",
            """[5] Launchers: Launches the icon through the air: 
the player can choose the target.""",
            """[6] More Locks: New locks that are more complex than 
the existing locks 'l' and 'L'."""
        ]
    )

    HOTKEYS = InfoData(
        header="Help for 'Edit Hotkeys':",
        bullets=[
            """Hotkeys help you quickly place a character without 
having to use your toolbar.""",
            """To create a hotkey, move down to the [+ New] bar 
and press [ENTER]. There, you can specify a hotkey, and the character 
it places.""",
            """You can edit the character a hotkey places. Just 
move to the hotkey you want to edit and press [ENTER] to get to 
the Edit / Delete menu.""",
            """In this same menu, you can also delete hotkeys.""",
            """You can always view your current hotkeys while 
editing by pressing [h].""",
            """(Some hotkeys cannot be used as they already have 
a use in the editor, such as w, a, s, d. Some characters are not 
supported for hotkeys yet.)"""
        ]
    )

    @classmethod
    def display_info(cls, name: str="GENERAL"):

        """Prints a help message for a certain area of the
        program."""

        clear()

        info_data = getattr(InfoUtils, name.strip().upper())
        stdout.write(str(info_data))

        IOUtils.input()

class EnterExitUtils:

    __slots__ = ()

    """Functions that control the intro scene and program exit."""

    LOGO = """                                 
                   &x&Xx&&   
                   :.&&...x. 
                 x.$;.....&&x
        ;&&&&&&$x:.;:.    .& 
      &&$;+X;:.+;.. . x;.;&. 
    x&x.:;:.:..:++..  ..:;   
   .&.  ;..$X;:  ..+.;.:.    
   &X+x;::.....:.:+x:+ ;+    
   &;.   .;..:.+&&x.  ::.    
   &X+:...::;:+.$;..   .     
   &X:x$;;;+.. ;&&$$ &&X     
   .&X$x:..Xx$$.   && &x     
    &&&&&&&&&&&&.. &;  &&.   
    ...............&&&. .$...
         .......... .........
Brought to you by: Capybara Studios [(C) 2026]"""[1:]

    CAPYBARA = """                                 
                   &x&Xx&&   
                   :.&&...x. 
                 x.$;.....&&x
        ;&&&&&&$x:.;:.    .& 
      &&$;+X;:.+;.. . x;.;&. 
    x&x.:;:.:..:++..  ..:;   
   .&.  ;..$X;:  ..+.;.:.    
   &X+x;::.....:.:+x:+ ;+    
   &;.   .;..:.+&&x.  ::.    
   &X+:...::;:+.$;..   .     
   &X:x$;;;+.. ;&&$$ &&X     
   .&X$x:..Xx$$.   && &x     
    &&&&&&&&&&&&.. &;  &&.   
    ...............&&&. .$...
         .......... ........."""[1:]

    TITLE = r"""
  m   .m,   mm  mmm  mmm        m   .m,   mm .mmm,.m .,.mmm,
 ]W[ .P'T  W''[ 'W'  'W'       ]W[ .P'T  W''[]P''`]W ][''W'`
 ]W[ ]b   ]P     W    W        ]W[ ]b   ]P   ][   ]P[][  W  
 W W  TWb ][     W    W        W W  TWb ][   ]WWW ][W][  W  
 WWW    T[]b     W    W        WWW    T[]b   ][   ][]d[  W  
.W W,]mmd` Wmm[ mWm  mWm      .W W,]mmd` Wmm[]bmm,][ W[  W  
'` '` ''`   ''  '''  '''      '` '` ''`   '' ''''`'` '`  '
ASCII Ascent: A Platformer Game [Capybara Studios (C) 2026]"""[1:]

    @classmethod
    def starting_scene(cls):

        """Runs the title scene."""

        clear()
        sleep(1)

        for line in EnterExitUtils.LOGO.splitlines():
            stdout.write(line + "\n")
            sleep(0.05)

        sleep(3)
        clear()

        for line in EnterExitUtils.TITLE.splitlines():
            stdout.write(line + "\n")
            sleep(0.05)

        sleep(3)
        clear()

        sleep(2)

    @classmethod
    def exit_scene(cls, string: str, *, exit_code: Literal[0, 1]=1):

        """Runs the exit scene. The exit scene usually also displays a user's
        save string. An argument for a message to display under the
        capybara is also required."""

        clear()
        exit_str = "\n".join([EnterExitUtils.CAPYBARA, "Thanks for playing!", string])
        stdout.write(exit_str.strip("\n"))

        raise SystemExit(exit_code) from None

class LoadUtils:

    __slots__ = ()

    """Creates the level loading visuals."""

    # Some goofy easter eggs.
    MSGS = [
        "Loading...",
        "Getting Characters...",
        "Placing Obstacles...",
        "Parsing Code...",
        "Flipping Bits...",
        "Getting Data...",
        "Doing Stuff...",
        "Running Algorithms...",
        "Creating the Fake Progress Bar... umm... wait nevermind.",
        "If you see this, you are incredibly lucky"
    ]

    # Their corresponding weights (makes the last one super rare)
    WEIGHTS = [1_000] * (len(MSGS) - 1) + [1]

    @staticmethod
    def progress_bar_iter(*, speed: float=1.0) -> Iterator[str]:

        """Given a speed of how fast to travel, returns a
        progress bar iterator that yields string bar representations.
        Note that at speed 1.0 (on default), it will take an average
        of e = 2.71... iterations for the iterator to stop
        (a cool fact from probability)."""

        percent: float = 0.0
        bar_length: int = Constants.X_LEN + 2

        while True:

            bar = "#" * int(percent * bar_length)

            yield f"{bar:-<{bar_length}}"

            if percent >= 1.0:
                break

            percent = min(percent + (random() / speed), 1.0)

    @classmethod
    def get_loading_msg(cls):

        """Gets a random easter egg loading message
        from MSGS."""

        return choices(cls.MSGS, weights=cls.WEIGHTS)[0]

    @staticmethod
    def _format_time(time: int | float):

        """Formats the time limit of a level for loading."""

        if isinstance(time, (int, float)) and time != float("inf"):
            return f"Time Goal: [{time:.2f} seconds]"
        else:
            return ""

    @staticmethod
    def _format_points(points: int):

        return f" [Points: {points}]" if points > 0 else ""

    @staticmethod
    def load(level: LevelData) -> None:

        """Displays visuals that 'load' a level. This function doesn't
        modify any data or return anything; it just shows a loading
        screen."""

        if level == LevelData.NULL:
            return

        bars = LoadUtils.progress_bar_iter()

        while True: # Print progress bar
            try:
                clear()

                header = (
                        LoadUtils._format_time(level.time)
                        + LoadUtils._format_points(level.points)
                )

                if header:
                    stdout.write(header + "\n")

                stdout.write(str(level.map))
                stdout.write(
                    LoadUtils.get_loading_msg() + "\n" + next(bars) + "\n"
                )

                sleep(random())

            except StopIteration:
                clear()
                break

    @staticmethod
    def load_scrolling(level: LevelData) -> None:

        """Loads a map similar to in LoadUtils.load, but now
        the map scrolls up and down. Additionally, the progress
        bar scrolls slower."""

        if level == LevelData.NULL:
            return

        y_len = len(level.map)

        bars = LoadUtils.progress_bar_iter(speed=12.0)

        bottom, top = 0, Constants.Y_LEN

        d = 1

        while True:

            try:

                display = level.map[bottom:top]

                clear()

                stdout.write(LoadUtils._format_time(level.time) + "\n")
                stdout.write(str(display))
                stdout.flush()

                stdout.write(LoadUtils.get_loading_msg() + "\n")
                stdout.write(next(bars) + "\n")
                stdout.flush()

                sleep(random())

                # How much to move up / down.
                if d == 1 and top >= y_len:
                    d = -1
                elif d == -1 and bottom <= 0:
                    d = 1

                # Adjust slices; move up or down
                top += d
                bottom += d

            except StopIteration:

                clear()
                break

class PaginateUtils:

    __slots__ = ()

    """PaginateUtils provides a function paginate_maps which lets users
    select from maps in a database and select one."""

    @staticmethod
    def paginate(database: LevelDatabase, /, *,
                 header: str=None, meta: bool=True, ind: int=0
                 ) -> tuple[int, LevelData]:

        """Read the PaginateUtils docstring. There are three optional
        parameters:
        - header: string to be shown at the top during pagination
        - meta: affects whether the author is shown
        - ind: the index to start pagination at (default 0)"""

        if not database:
            raise ValueError

        max_ind = len(database) - 1

        while True:
            clear()

            if header is not None:
                stdout.write(header + "\n")

            level = database[ind] # LevelData

            title, author, _, desc, game_map, time, __, points = level

            # From textwrap.
            desc_str = shorten(desc, width=50, placeholder="...")

            if desc_str:
                desc_str = f"[{desc_str}]"

            title_str = f"[{title}]".upper()

            points_str = f"[Points: {points}]" if points > 0 else ""

            author_str = f"[Created by: {author}]" if meta else ""

            time_str = LoadUtils._format_time(time)

            # Always 3 lines long. Prevents shifting between maps
            stdout.write(
                f"""{title_str} {author_str}\n{time_str} {points_str}\n{desc_str}\n"""
            )
            stdout.write(str(game_map))

            stdout.write("Page:".center(Constants.X_LEN + 2) + "\n")
            if ind == 0:
                arrow = "|1 >|" if len(database) != 1 else "|1|"
            elif ind == max_ind:
                arrow = f"|< {ind + 1}|"
            else:
                arrow = f"|< {ind + 1} >|"

            stdout.write(arrow.center(Constants.X_LEN + 2) + "\n")

            a = IOUtils.input(
                "[a]/[d] to scroll, [x] to exit, [ENTER] to continue. "
            )

            if a == "d" and ind != max_ind:
                ind += 1
            elif a == "a" and ind != 0:
                ind -= 1
            elif a in {"exit", "x"}:
                return None, LevelData.NULL
            elif not a:
                break

        return ind, database[ind]

class Achievements:

    __slots__ = ()

    """The game's achievements. Nothing else to see here."""

    ACHIEVEMENTS = dict(
        [
            # Progress / coin related achievements
            ("Getting Started", "Beat one level"),
            ("Above Average", "Beat a level with a coin"),
            ("ASCII Rookie", "Beat 5 levels"),
            ("ASCII Novice", "Beat 10 levels"),
            ("ASCII Master", "Beat the Tower"),
            ("ASCII King?", "Beat all levels"),
            ("The Richest", "Beat 10 levels with all coins"),
            ("Maxxed Out", "Beat all levels with coins and in time"),

            # Point related achievements
            ("Ten Squared", "Earn 100 points"),
            ("Two Times Better", "Earn 200 points"),
            ("How on Earth?", "Earn 500 points"),

            # Jump related achievements
            ("Jumping Maniac", "Jump 100 times"),

            # Attempt related achievements
            ("Never Give Up", "Get 20 attempts"),

            # Time related achievements
            ("Speedrunner", "Beat a level under the time limit"),
            ("Master Speedrunner", "Beat 10 levels under the time limit"),
            ("Need for Speed", "Beat a level in under 3 seconds"),
        ]
    )

# Type aliases
num = int | float
vector = tuple[num, num]

class PerlinNoise:

    __slots__ = ("gradients",)

    """A class which contains the .noise() method, which returns
    a value based on x and y coordinates. It also contains .display(),
    which can be used to create a visualization with a certain length
    and height."""

    PERMUTATIONS = list(range(256))
    shuffle(PERMUTATIONS)

    def __init__(self):

        self.gradients = self._create_gradients()

    def _create_gradients(self):

        """Generates a list of 256 random unit vectors using basic
        trigonometry."""

        def unit_vector(deg: int):
            return (cos(radians(deg)), sin(radians(deg)))

        degrees = sample(range(360), k=256)

        # Create a list of random unit vectors.
        return [unit_vector(deg) for deg in degrees]

    def _get_gradient(self, ix: int, iy: int):

        """Finds the gradient vector from self.gradients
        at a certain coordinate."""

        i = (ix % 256 + PerlinNoise.PERMUTATIONS[iy % 256]) % 256
        index = PerlinNoise.PERMUTATIONS[i]

        return self.gradients[index % 256]

    @staticmethod
    def _dot_product(v1: vector, v2: vector) -> num:

        """Helper function to return the dot product of two vectors in R^2."""

        return v1[0] * v2[0] + v1[1] * v2[1]

    @staticmethod
    def _easing(a: num) -> num:

        """Smoothstep function 3a^2 - 2a^3."""

        return 3 * pow(a, 2) - 2 * pow(a, 3)

    @staticmethod
    def linear(h1: num, h2: num, frac: num) -> float:

        """Linear interpolation formula using smoothstep, aka lerp()."""

        return h1 + PerlinNoise._easing(frac) * (h2 - h1)

    @staticmethod
    def bilinear(n00: num, n10: num, n01: num, n11: num, xf: num, yf: num):

        """Bilinear interpolation formula using linear interpolation.
        The first four arguments in this case are the dot products."""

        v0 = PerlinNoise.linear(n00, n10, xf)
        v1 = PerlinNoise.linear(n01, n11, xf)

        v = PerlinNoise.linear(v0, v1, yf)

        return v

    def noise(self, x: num, y: num) -> float:

        """Generates the Perlin Noise value based on a coordinate
        x and y.

        Key for variable names:

        01    11


        00    10

        """

        ix, iy = floor(x), floor(y)

        # Decimal parts of x and y.

        xf: num
        yf: num

        xf, yf = x - ix, y - iy

        # Gradient vectors.

        g00: vector
        g10: vector
        g01: vector
        g11: vector

        g00 = self._get_gradient(ix, iy)
        g10 = self._get_gradient(ix + 1, iy)
        g01 = self._get_gradient(ix, iy + 1)
        g11 = self._get_gradient(ix + 1, iy + 1)

        # The dot products of the offset vectors and gradient vectors.

        n00: num
        n10: num
        n01: num
        n11: num

        n00 = PerlinNoise._dot_product((xf, yf), g00)
        n10 = PerlinNoise._dot_product((xf - 1, yf), g10)
        n01 = PerlinNoise._dot_product((xf, yf - 1), g01)
        n11 = PerlinNoise._dot_product((xf - 1, yf - 1), g11)

        return self.bilinear(n00, n10, n01, n11, xf, yf)
