from __future__ import annotations

# Builtins
from dataclasses import dataclass, field
from typing import Callable, ClassVar
from sys import stdout
from itertools import zip_longest

# For save strings
import pickle
import base64
from zlib import compress, decompress
import textwrap

# Other modules (in this directory)
from clear import clear
from plat import Platformer, Tower, Result
from utils import (InfoUtils, EnterExitUtils, LoadUtils,
                   PaginateUtils, Achievements, StringUtils, IOUtils)
from maps import (MAIN_RANGE, GLOBAL_DATABASE, LevelData, Constants,
                  SerializationError)
from anim import (Cutscene, Tutorial, ENDING_DATA, PLATFORMER_TUTORIAL,
                  INTRO_DATA)

from hashlib import sha256
from editormode import Hotkeys
import othermodes as m

"""[game.py] Contains main(), the main loop
where users can play levels and view their progress."""

class Console:

    """A class that implements the Character Selection Screen as
    well as getting usernames."""

    __slots__ = ()

    OPTIONS = r"Oo0&"

    SCALED = {

        "O": r"""
    #########
  ###       ###
 ##           ## 
 #  .     .    #  
##             ##
#      o        #
##             ##
 #             #
 ##           ##
  ###       ###
    #########
"""[1:],

        "o": """


    
    #########
  ###       ###
 ##           ##
##   U   U     ##
##             ##
 ##    __/    ##
  ###       ###
    #########
"""[1:],

        "&": """
     ####        
   ######## 
  ## o o ### 
  ##  .  ###    
  ###   ###      
   ######        
  ######    ###  
###    ###  ###  
##      ### ###  
####      ####   
   ########  ####
"""[1:],

        "0": """
    #########
  ###       ###
 ##      _    ## 
 #   _         #  
##   O   O ######
#     #####     #
###### O       ##
 #             #
 ##           ##
  ###       ###
    #########
"""[1:]

    }

    LENGTH = 17

    MSG = "Select characters using [A] or [D], press [ENTER] when done:"

    @classmethod
    def _get_display_from_icon(cls, icon: str):

        """Given an icon, returns the screen that displays in the selection
        menu."""

        scaled_center = Console.SCALED[icon]

        lines = [
            "~" * (Console.LENGTH + 4),
            *(("| " + line[:Console.LENGTH].ljust(Console.LENGTH) + " |")
              for line in scaled_center.splitlines()),
            "~" * (Console.LENGTH + 4)
        ]

        bar_len = len(Console.MSG) - (Console.LENGTH + 4)

        bar = [
            "Options (cycle using [A]/[D]):",
            *(f"| {i} {'<' if i == icon else ''}".ljust(bar_len)
              for i in Console.OPTIONS)
        ]

        bar = [line.ljust(bar_len) for line in bar]

        fill_value = "|".ljust(bar_len)

        display = [
            "".join([icon_str, line])
            for icon_str, line in zip_longest(bar, lines, fillvalue=fill_value)
        ]

        display = "\n".join(display) + "\n"

        return display

    @classmethod
    def get_icon(cls, *, current_icon=None) -> str:

        """Gets the player icon using a scrolling interface."""

        if current_icon is None:
            ind = 0
            current_icon = Console.OPTIONS[ind]
        else:
            ind = Console.OPTIONS.find(current_icon)

        i = len(Console.OPTIONS)
        while True:
            clear()

            icon: str = Console.OPTIONS[ind]

            stdout.write(Console.MSG + "\n")
            stdout.write(Console._get_display_from_icon(icon))

            choice = IOUtils.input("Select / Move: ")

            if not choice:
                return icon
            elif choice.lower() in frozenset("wa"):
                ind -= 1
            elif choice.lower() in frozenset("sd"):
                ind += 1

            ind %= i

    @staticmethod
    def get_username(current_username=None):

        current = ("" if current_username is None else
                   f" [Current username: {current_username}]"
                   )

        input_str = \
            f"""What would you like your username to be?
[Under {LevelData.MAX_AUTHOR_WIDTH} characters]{current}\n"""
        while True:

            clear()

            stdout.write(input_str)
            username = IOUtils.input("-> ").strip()

            if len(username) > LevelData.MAX_AUTHOR_WIDTH or not username:
                continue

            return username

class MainProgress(m.Progress):

    """A subclass of Progress (dictionary that maps level IDs to
    Status objects), used to keep track of progress on the 50 main
    levels."""

    db = GLOBAL_DATABASE

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    @property
    def score(self):

        """
        Sums up the total score based on the results for each level.
        Note that this is not the definitive score. The points coming from
        Endless Mode and Custom Levels also need to be added as well.
        """

        return sum(
            level.score(self[level.id].result)
            for level in MainProgress.db
        )

    def view(self, r: range=MAIN_RANGE):

        """View your progress for a specific range of levels."""

        clear()

        stdout.write(StringUtils.divider() + "\n")

        strings = []

        for i in r:

            level_id = GLOBAL_DATABASE[i - 1].id

            r = self[level_id].result

            title = "Tower" if i == Constants.TOWER else str(i)

            strings.append(f"{title}: {r!s}")

        stdout.write(StringUtils.format_columns(strings, cols=2) + "\n")
        stdout.write(StringUtils.divider() + "\n")

        IOUtils.input("Press [ENTER] to continue. ")

@dataclass(slots=True)
class Stats:

    """A class that holds information on jumps, attempts,
    and other statistics about the user."""

    jumps: int = 0
    attempts: int = 0
    total_time: float = 0.0 # Total time spent playing levels

    def __repr__(self):

        return "Stats(jumps={}, attempts={}, total_time={})".format(
            self.jumps,
            self.attempts,
            self.total_time
        )

    def __post_init__(self):

        for i in "jumps", "attempts":
            attr = getattr(self, i)
            if not isinstance(attr, int):
                raise ValueError(f"Received wrong value for {i}.")
            elif attr < 0:
                raise ValueError(f"Attribute '{i}' is negative.")

        if not isinstance(self.total_time, float):
            raise ValueError("Received wrong value for total_time.")
        elif self.total_time < 0.0:
            raise ValueError("total_time is negative.")

    @classmethod
    def from_tuple(cls, t: tuple):

        """Create a Stats object from a tuple."""

        return Stats(*t)

    def view(self):

        """Lets the user view their statistics easily."""

        clear()

        str_lst = [
            f"Total Attempts: {self.attempts}",
            f"Total Jumps: {self.jumps}"
        ]

        stdout.write(StringUtils.bar(str_lst, width=Constants.X_LEN) + "\n")

        IOUtils.input("Press [ENTER] to continue. ")

@dataclass(slots=True)
class MainSettings:

    display_desc: bool=True
    display_coords: bool=False
    display_percentage: bool=True
    autoplay: bool=False

    NAMES: ClassVar[dict[str, str]] = {
        "display_desc": "Display Description",
        "display_coords": "Display Coordinates",
        "display_percentage": "Display Percentage",
        "autoplay": "Autoplay",
    }

    INFO: ClassVar[dict[str, str]] = {
        "display_desc": """Whether the level description
is displayed or hidden while playing. (The description of a 
level can always be viewed by typing 'desc' or 'e'.)""",
        "display_coords": """Whether your coordinates 
are displayed or hidden while playing. Turned off by default.""",
        "display_percentage": """Whether the percentage
is displayed or hidden while playing. Turned on by default.""",
        "autoplay": """Whether after beating a main level, 
the next level will automatically be played. Turned off by 
default. (If this option is selected, type 'exit' to stop 
playing.)"""
    }

    def __post_init__(self):

        for attr in MainSettings.__slots__:
            if not isinstance(getattr(self, attr), bool):
                raise TypeError(f"{attr} is not of type bool.")

    def __repr__(self):

        return "MainSettings(display_desc={}, display_coords={}, autoplay={})".format(
            self.display_desc,
            self.display_coords,
            self.autoplay
        )

    def toggle(self, attr_name: str):

        current = getattr(self, attr_name)

        setattr(self, attr_name, not current)

    def display_info(self, attr_name: str):

        clear()

        divider = StringUtils.divider(width=Constants.X_LEN) + "\n"

        stdout.write(divider)

        string = ": ".join((
            MainSettings.NAMES[attr_name],
            MainSettings.INFO[attr_name].replace("\n", "")
        ))

        stdout.write(textwrap.fill(string, width=Constants.X_LEN) + "\n")

        stdout.write(divider)

        IOUtils.input("Press [ENTER] to continue. ")

    def gui(self, current_attr: str):

        result = []

        divider = StringUtils.divider(width=Constants.X_LEN)

        result.append(divider)

        for attr_name, setting_name in MainSettings.NAMES.items():

            on_off = "[o]" if getattr(self, attr_name) else "[x]"
            arrow = "<" if attr_name == current_attr else " "

            result.append(f"{setting_name:<57} {on_off} {arrow}")

        result.append(divider)

        result.append(
            "[w]/[s] to select, [i] for info, [ENTER] to toggle, [x] to exit."
        )

        return "\n".join(result) + "\n"

    def edit(self):

        current_ind = 0

        n = len(MainSettings.__slots__)

        while True:

            current_attr = MainSettings.__slots__[current_ind]

            clear()

            stdout.write(self.gui(current_attr))

            selection = IOUtils.input("-> ", sanitize=True)

            match selection:

                case "w" | "a":

                    current_ind = (current_ind - 1) % n

                case "s" | "d":

                    current_ind = (current_ind + 1) % n

                case "i":

                    self.display_info(current_attr)

                case "":

                    self.toggle(current_attr)

                case "x":

                    return

@dataclass(slots=True)
class MainData:

    """MainData is a class that stores all the user's
    data for main levels, as well as 'account data'.
    This includes:
    - the user's icon
    - the user's name
    - the user's progress (a dict of Result objects for each level)
    - the user's stats (a dict of the user's account statistics)
    - Whether the user has unviewed achievements or not.
    """

    # Prompts user for username
    username: str = field(default_factory=Console.get_username)

    # Prompts user for icon
    icon: str = field(default_factory=Console.get_icon)

    progress: MainProgress = field(default_factory=MainProgress)

    stats: Stats = field(default_factory=Stats)

    unviewed: bool = False

    settings: MainSettings = field(default_factory=MainSettings)

    def __repr__(self):

        return "MainData(username={}, icon={}, progress={}, stats={}, unviewed={}, settings={})".format(
            repr(self.username),
            repr(self.icon),
            repr(self.progress),
            repr(self.stats),
            repr(self.unviewed),
            repr(self.settings)
        )

    def __post_init__(self):

        if not isinstance(self.username, str):
            raise TypeError("Username is not a string.")
        if not isinstance(self.icon, str):
            raise TypeError("Icon is not a string.")
        elif len(self.icon) != 1:
            raise ValueError("Icon is not 1 character.")

        if not isinstance(self.progress, MainProgress):
            raise TypeError("Progress is not of type MainProgress.")
        if not isinstance(self.stats, Stats):
            raise TypeError("Stats is not of type Stats.")

        if not isinstance(self.unviewed, bool):
            raise TypeError("Unviewed is not a boolean.")
        if not isinstance(self.settings, MainSettings):
            raise TypeError(
                "Setting is not of type MainSettings."
            )

    def all_levels(self, upto=Constants.TOWER):

        """Calculates whether all levels have been beaten up to a
        certain level, specified by the 'upto' argument. Set to
        20 on default, so all_levels calculates whether the first 20
        levels have been beaten. This is a necessary requirements for
        things like the Level Packs."""

        p = self.progress

        db_slice = GLOBAL_DATABASE[:upto]

        return all(bool(p[level.id].result) for level in db_slice)

    def next_level(self, upto=len(GLOBAL_DATABASE)):

        """Finds the first level that has not been beaten yet. The
        optional 'upto' argument, at default set to 50, makes it so
        if all the levels below it have been beaten, next_level
        automatically returns upto, regardless of whether upto itself has
        been beaten. This is used in the 'Continue Game' and 'Select Level'
        options."""

        if upto > len(GLOBAL_DATABASE):
            raise ValueError(
                "upto is larger than the number of levels in GLOBAL_DATABASE."
            )

        p = self.progress

        for i, level in enumerate(GLOBAL_DATABASE, 1):

            if i == upto or p[level.id].result == Result.NONE:
                return i

    @property
    def main_score(self):

        """Another name for the score in self.progress. This is
        added to custom_score and endless_score to find the
        total score the user has."""

        return self.progress.score

@dataclass(slots=True)
class Data:

    """Consolidates all data relating to the user in one place.
    This is the data that gets serialized in save strings.
    All other data such as Achievements can be derived from the
    data stored in this object. Crucially, EditorData is not
    stored in this object, since the user can choose to save
    and share each individual level in its own save string."""

    main_data: MainData = field(default_factory=MainData)
    custom_data: m.CustomData = field(default_factory=m.CustomData)
    endless_data: m.EndlessData  = field(default_factory=m.EndlessData)

    achievement_data: AchievementData = field(init=False)

    def __post_init__(self):

        if not isinstance(self.main_data, MainData):
            raise ValueError(
                "Did not receive MainData object for self.main_data"
            )
        if not isinstance(self.custom_data, m.CustomData):
            raise ValueError(
                "Did not receive CustomData object for self.custom_data"
            )
        if not isinstance(self.endless_data, m.EndlessData):
            raise ValueError(
                "Did not receive EndlessData object for self.endless_data"
            )

        self.achievement_data = AchievementData(self)
        self.achievement_data.update()

    @property
    def score(self):

        """Sums up the scores from main levels, custom levels
        and Endless mode to create the user's total score."""

        return (self.main_data.main_score
                + self.custom_data.custom_score
                + self.endless_data.endless_score
                + self.achievement_data.achievement_score
                )

    @property
    def checksum(self):

        strs = (
            repr(self.main_data),
            repr(self.custom_data),
            repr(self.endless_data)
        )

        binary = [
            string.encode("utf-8").replace(b"\x00", b"")
            for string in strs
        ]

        bytes_obj = b"\x00".join(binary)

        return sha256(bytes_obj).hexdigest()

    def as_stuple(self):

        return (
            self.main_data,
            self.custom_data,
            self.endless_data,
            self.checksum
        )

    @classmethod
    def from_stuple(cls, args: tuple):

        data, checksum = args[:-1], args[-1]

        new = cls(*data)

        if new.checksum != checksum:
            raise ValueError(
                "Save string was manipulated; checksum does not match"
            )
        else:
            return new

    @classmethod
    def from_save_str(cls, save_str: str, /) -> Data:

        """Creates a Data object from a save string."""

        try:
            decoded = decompress(base64.a85decode(save_str.encode("utf-8")))
            data = pickle.loads(decoded)
            return cls.from_stuple(data)
        except Exception as e:

            raise SerializationError(str(e)) from e

    def as_save_str(self):

        """Creates a save string from a Data object."""

        encoded = compress(pickle.dumps(self.as_stuple()))

        save_str = base64.a85encode(encoded)
        return save_str.decode("utf-8").strip()

    def __repr__(self):

        return \
            f"Data({self.main_data}, {self.custom_data}, {self.endless_data})"

class AchievementData:

    SCORE = 5

    def __init__(self, data):

        self.achievements = {i: False for i in Achievements.ACHIEVEMENTS}
        self.data = data

    @property
    def achievement_count(self):

        return sum(1 for i in self.achievements if self.achievements[i])

    @property
    def achievement_score(self):

        return self.achievement_count * AchievementData.SCORE

    def update(self):

        """Updates achievements based on a Data object. Returns whether
        anything was updated or not."""

        def number_of(cond: Callable, lst=None):

            """Finds the number of elements in a list
            that satisfy a particular condition specified
            by cond. The list is set to results by default."""

            if lst is None:
                lst = results

            return sum(1 for i in lst if cond(i))

        statuses = self.data.main_data.progress.values()

        results = [s.result for s in statuses]
        times = [s.time for s in statuses]

        s = self.data.main_data.stats

        max_flags = Result.WON | Result.COIN | Result.TIME

        levels_beaten = number_of(lambda x: x != Result.NONE)
        levels_maxxed = number_of(lambda x: x == max_flags)
        coins = self.data.main_data.progress.coins
        under_time = number_of(lambda x: Result.TIME in x)
        under_3 = number_of(lambda x: x < 3.0, times)

        def update(name: str, cond: bool):

            """Updates the achievement with a given name based
            on cond. If cond is true and the achievement
            isn't already achieved, then it will update it."""

            if self.achievements[name] is False and cond:
                self.achievements[name] = True
                return True
            else:
                return False

        tower_id = GLOBAL_DATABASE[Constants.TOWER - 1].id
        tower_result = self.data.main_data.progress[tower_id].result

        items = [

            ("Getting Started", levels_beaten > 0),
            ("Above Average", coins > 0),

            ("ASCII Rookie", levels_beaten >= 5),
            ("ASCII Novice", levels_beaten >= 10),
            ("ASCII Master", bool(tower_result)),
            ("ASCII King?", self.data.main_data.all_levels()),

            ("The Richest", coins >= 10),

            ("Maxxed Out", levels_maxxed == 20),

            ("Ten Squared", self.data.score >= 100),
            ("Two Times Better", self.data.score >= 200),
            ("How on Earth?", self.data.score >= 500),

            ("Jumping Maniac", s.jumps >= 100),
            ("Never Give Up", s.attempts >= 20),

            ("Speedrunner", under_time >= 1),
            ("Master Speedrunner", under_time >= 10),
            ("Need for Speed", under_3 > 0)

        ]

        updated = False

        for x in items:
            if update(*x):
                updated = True

        return updated

    def view(self):

        """Views achievements using a simple two-page pagination
        mechanism."""

        second_page = False
        achievement_list = list(self.achievements.items())

        while True:

            clear()

            page_slice = (
                slice(8, None, None) if second_page else
                slice(None, 8, None)
            )

            stdout.write(StringUtils.divider() + "\n")

            for name, status in achievement_list[page_slice]:

                desc = Achievements.ACHIEVEMENTS[name]
                status_str = f'[{AchievementData.SCORE}]' if status else '[0]'
                bulletpoint = f"{name.upper()}: {desc}"

                stdout.write(f"- {bulletpoint:<58}{status_str}\n")

            stdout.write(StringUtils.divider() + "\n")
            stdout.write("Page:".center(Constants.X_LEN) + "\n")

            arrow = "|< 2|" if second_page else "|1 >|"
            stdout.write(arrow.center(Constants.X_LEN) + "\n")

            selection = IOUtils.input(
                "Use a/d to scroll, press [ENTER] to continue. ").strip()

            if selection == "a":
                second_page = False
            elif selection == "d":
                second_page = True
            elif not selection:
                break

class LevelPlayer:

    def __init__(self, main_data: MainData):

        self.main_data = main_data

    def play_level(self, map_num: int, /, *, load=True):

        """Plays a main level based on its number, and updates data
        and statistics after playing."""

        tower = map_num == Constants.TOWER

        if tower and self.main_data.progress.coins < 10:
            return

        clear()

        level = GLOBAL_DATABASE[map_num - 1]
        level_id = level.id

        # Adjust functions based on Tower mode.
        load_map = LoadUtils.load_scrolling if tower else LoadUtils.load
        plat_cls = Tower if tower else Platformer

        if load:
            load_map(level)

        platformer = plat_cls(
            level,
            icon=self.main_data.icon,
            meta=False,
            display_desc=self.main_data.settings.display_desc,
            display_coords=self.main_data.settings.display_coords,
            display_percentage=self.main_data.settings.display_percentage
        )

        new_status, jumps = platformer.play()

        self.main_data.progress.update_id(level_id, new_status)

        # Beat the Tower; show animation
        if tower and new_status.result.value > 0:
            Cutscene(ENDING_DATA,
                     icon=self.main_data.icon,
                     username=self.main_data.username
                     ).run(allow_skip=True)

        if level != LevelData.NULL: # didn't exit from paginate_maps.
            self.main_data.stats.attempts += 1

        self.main_data.stats.total_time += new_status.time

        self.main_data.stats.jumps += jumps

        if (self.main_data.settings.autoplay
                and new_status.result.value > 0
                and map_num < Constants.TOWER - 1):

            # Clear memory
            del platformer, plat_cls, load_map, level, level_id

            # Does not autoplay Tower.
            self.play_level(map_num + 1, load=False)

    def _select_level(self):

        """Handles the second option 'Select Level', where
        users can choose to play a level up to what they
        have unlocked. Returns the level number the user
        has selected."""

        n = min(self.main_data.next_level(upto=Constants.TOWER), Constants.TOWER - 1)
        unlocked_maps = GLOBAL_DATABASE[:n]

        # Do not show author and date of creation: meta=False
        map_num, _ = PaginateUtils.paginate(unlocked_maps, meta=False)

        if map_num is None:
            return None

        return map_num + 1

    def select_level(self):

        map_num = self._select_level()

        if map_num is not None:
            self.play_level(map_num)

    def continue_game(self):

        level_num = self.main_data.next_level(upto=Constants.TOWER)
        self.play_level(level_num)

    @property
    def gui(self):

        level_num = self.main_data.next_level(upto=Constants.TOWER)
        level = GLOBAL_DATABASE[level_num - 1]

        coins = self.main_data.progress.coins >= 10

        if level_num == Constants.TOWER:
            option1 = "Play Tower" if coins else "----------"
        else:
            option1 = "Continue Game"

        level_map = level.map

        if level_num == Constants.TOWER:
            level_map = level_map[:Constants.Y_LEN]

        bar = StringUtils.distribute(StringUtils._enumerated(
            [
                option1,
                "Select Level",
                "Info",
                "Exit",
            ]
        ), width=Constants.X_LEN - 2
        )

        unlocked = ('Locked, collect 10 coins first'
                    if not coins else "")

        next_level = f'TOWER {unlocked}' if level_num == Constants.TOWER else level.title

        header = f"Next Level: {next_level}"

        bar = f"| {bar} |"

        return f"{header}\n{level_map!s}{bar}\n{'~'*(Constants.X_LEN + 2)}\nSelect a number: "

    def run(self):

        while True:

            clear()
            stdout.write(self.gui)

            selection = IOUtils.input(sanitize=True)

            match selection.strip().lower():

                case "1":

                    self.continue_game()

                case "2":

                    self.select_level()

                case "i":
                    InfoUtils.display_info("GAME")

                case "x":

                    break

class AccountViewer:

    def __init__(self, main_mode: MainMode):

        self.m = main_mode

    @property
    def icon_str(self):

        icon = self.m.data.main_data.icon

        scaled_center = Console.SCALED[icon]

        lines = [
            "~" * (Console.LENGTH + 4),
            *(("| " + line[:Console.LENGTH].ljust(Console.LENGTH) + " |")
              for line in scaled_center.splitlines()),
            "~" * (Console.LENGTH + 4)
        ]

        return lines

    @property
    def _gui(self):

        initial = [
            f"Your username: {self.m.data.main_data.username}",
            f"Your icon: {self.m.data.main_data.icon}",
        ]
        subs = {
            2: "(!)" if self.m.data.main_data.unviewed else ""
        }

        actions = StringUtils._enumerated([
            "View Stats",
            "View Progress",
            "View Achievements",
            "Change Icon",
            "Change Username",
        ])

        width = 11 + len(self.m.data.main_data.username)
        min_width = len(max(actions, key=len))
        width = max(width, min_width)

        initial.extend(StringUtils.list_box([
            line.ljust(width) for line in actions
        ], subs=subs).splitlines())

        under_actions = [
            "[6] Settings",
            "[i] Info",
            "[x] Exit",
        ]

        initial.extend(StringUtils.list_box([
            line.ljust(width) for line in under_actions
        ]).splitlines()[1:])

        return initial

    @property
    def gui(self):

        icon_str = self.icon_str

        gui = [" ".join((line1, line2)) for line1, line2 in zip_longest(
            icon_str, self._gui, fillvalue="")]

        return "\n".join(gui)

    def view(self):

        while True:

            clear()

            stdout.write(self.gui + "\n")
            selection = IOUtils.input("Choose a number: ", sanitize=True)

            match selection:

                case "1":

                    self.m.data.main_data.stats.view()

                case "2":

                    self.m.data.main_data.progress.view()

                case "3":

                    self.m.data.achievement_data.view()
                    self.m.data.main_data.unviewed = False

                case "4":

                    self.m.data.main_data.icon = Console.get_icon(
                        current_icon=self.m.data.main_data.icon
                    )

                case "5":

                    new_username = Console.get_username(
                        current_username=self.m.data.main_data.username
                    )

                    self.m.editor_data.rewrite_author(new_username)
                    self.m.data.main_data.username = new_username

                case "6":

                    self.m.data.main_data.settings.edit()

                case "i":

                    InfoUtils.display_info("ACCOUNT")

                case "x":

                    break

class Intro:

    __slots__ = ()

    GUI = r"""
  m   .m,   mm  mmm  mmm        m   .m,   mm .mmm,.m .,.mmm,
 ]W[ .P'T  W''[ 'W'  'W'       ]W[ .P'T  W''[]P''`]W ][''W'`
 ]W[ ]b   ]P     W    W        ]W[ ]b   ]P   ][   ]P[][  W  
 W W  TWb ][     W    W        W W  TWb ][   ]WWW ][W][  W  
 WWW    T[]b     W    W        WWW    T[]b   ][   ][]d[  W  
.W W,]mmd` Wmm[ mWm  mWm      .W W,]mmd` Wmm[]bmm,][ W[  W  
'` '` ''`   ''  '''  '''      '` '` ''`   '' ''''`'` '`  '
ASCII Ascent: A Platformer Game [Capybara Studios (C) 2026]
[1] New Game [2] Load Game [i] About Game
-> """[1:]

    @staticmethod
    def _load_data():

        clear()

        header_box = StringUtils.text_box(
            """Save strings allow you to save your data
across different playthroughs. Paste your string here to load
your game."""
        )

        error_box = StringUtils.text_box(
            """There was an error loading your save string.
Please try again, or restart the program to start a new game."""
        )

        error = False

        while True:

            stdout.write("You selected: Load Game\n")

            string = error_box if error else header_box

            stdout.write(string)

            savestr = IOUtils.input("Paste save string here: ")

            error = (savestr and not savestr.isspace())

            clear()

            try:
                data = Data.from_save_str(savestr)
            except SerializationError:
                continue

            break

        clear()

        return data

    @staticmethod
    def _get_data():

        """First gets the data from the user. People can
        either create a new game, load a preexisting
        game using their save string, or view info
        about the game.

        The 'secret' mode is meant for development.
        It skips the intro scene and gets straight
        to creating a username, picking icons, etc.
        """

        while True:

            clear()
            selection = IOUtils.input(Intro.GUI)

            match selection:

                case "1":
                    clear()
                    EnterExitUtils.starting_scene()
                    return Data(), True
                case "2":
                    return Intro._load_data(), False
                case "i":
                    InfoUtils.display_info()
                    continue
                case _:
                    continue

    @staticmethod
    def get_data():

        try:

            data, intro = Intro._get_data()

            if intro:

                Cutscene(INTRO_DATA, icon=data.main_data.icon,
                         username=data.main_data.username).run()

            return data

        except (Exception, KeyboardInterrupt):

            EnterExitUtils.exit_scene(
                "Your game ended unexpectedly. Thanks for playing!"
            )

class MainMode:

    """The main game loop for the Platformer game.
    Handles the main menu and the operations for playing
    levels."""

    __slots__ = (
        "data",
        "editor_data",
        "hotkeys",
    )

    def __init__(self, *, savestr: str=None):

        """MainMode only has three attributes, data, editor_data
        and hotkeys.

        self.data: The main Data object for the user.
        self.editor_data: The levels that the user has created.
        Stored while program is running, but cannot be serialized.
        Instead, individual levels can be saved by the user."""

        if savestr:
            try:
                self.data = Data.from_save_str(savestr)
            except SerializationError:

                raise
                clear()
                IOUtils.input(
                    """There was an error loading your save string.
                    Sending you to the title screen.
                    Press [ENTER] to continue. """)

                self.data = Intro.get_data()

        else:
            self.data = Intro.get_data()

        self.hotkeys = Hotkeys()

        self.editor_data = m.EditorData()

    @property
    def gui(self):

        """Creates the GUI for the main menu."""

        achievement_sub = "(!)" if self.data.main_data.unviewed else ""

        # Displays 'Unlocked' if the first 19 levels are beaten.
        tower_sub = ("" if self.data.main_data.all_levels(upto=Constants.TOWER - 1)
                     else "(Unlock by beating Tower)")

        str_list = [
            "Play",
            "Creator",
            "Endless",
            "Level Packs",
            "View Account",
            "Save",
            "Tutorial",
            "About Game",
            "Exit"
        ]

        subs = {
            3: tower_sub,
            4: achievement_sub
        }

        header = "[{}] [Score: {}] [You are: {}]".format(
            self.data.main_data.username,
            self.data.score,
            self.data.main_data.icon
        )

        return StringUtils.menu(header, str_list, subs=subs)

    def _update_achievements(self):

        """Updates achievements based on the player's Data object.

        Note: Call this function AS SPARINGLY AS POSSIBLE. This operation is
        incredibly computationally intensive, so keep the function calls to a
        minimum. This is exactly what is done in _run using the 'update' flag.
        """

        new = self.data.achievement_data.update()

        if self.data.main_data.unviewed is False:
            self.data.main_data.unviewed = new

    def get_selection(self):

        """Displays the GUI for the main menu and gets the user's input."""

        selection = IOUtils.input(self.gui, sanitize=True)
        return selection

    def _run(self) -> None:

        """The main game loop for the Platformer.
        It essentially takes the player's selections
        and executes them on a loop."""

        while True:

            clear()

            selection = self.get_selection()

            update = True # Whether achievements should update.
            match selection:

                case "1": # Play
                    LevelPlayer(self.data.main_data).run()

                case "2": # Creator
                    self.data, self.editor_data = m.CustomMode(self.data,
                                                               self.hotkeys,
                                                               self.editor_data).run()

                case "3": # Endless
                    self.data = m.EndlessMode(self.data).run()

                case "4": # Level Packs

                    if self.data.main_data.all_levels():
                        self.data = m.PackMode(self.data).run()

                case "5":

                    AccountViewer(self).view()
                    update = False

                case "6": # Save Game

                    clear()
                    stdout.write("Your save string is below:\n")
                    stdout.write(self.data.as_save_str() + "\n")
                    IOUtils.input("Press [ENTER] to continue. ")
                    update = False

                case "7":

                    Tutorial(PLATFORMER_TUTORIAL, self.data.main_data.icon
                             ).run()

                case "8":

                    InfoUtils.display_info()

                case "x": # Exit

                    save_str = self.data.as_save_str()
                    string = f"Your save string is below:\n{save_str}\n"
                    EnterExitUtils.exit_scene(string)
                    return

                case _: # Wildcard; nothing happens. Do not update.

                    update = False

            if update:
                self._update_achievements()

    def run(self):

        """A wrapper function around _run that will exit the program
        and display their save string in red if their device shuts
        down. This is so people can save their progress instead of
        losing it."""

        try:
            self._run()
        except (Exception, KeyboardInterrupt):

            # __import__("traceback").print_exc()
            # input()

            save_str = self.data.as_save_str()
            EnterExitUtils.exit_scene(
                f"Your game ended unexpectedly. Your save string is below:\n{save_str}"
            )
