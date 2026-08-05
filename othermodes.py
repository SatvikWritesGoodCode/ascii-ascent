from __future__ import annotations

from typing import Literal, TypeVar
from clear import clear
from plat import Endless, Platformer, Result, Status, GenerationParameters
from time import sleep
from utils import (
    LoadUtils,
    PaginateUtils,
    InfoUtils,
    StringUtils,
    IOUtils
)
from maps import SHOWCASE_DATABASE, PUBLIC_DATABASE, PACKS, Constants
from math import isnan
from dataclasses import dataclass
from maps import LevelData, LevelDatabase, PACK_RANGE
from editormode import EditorMode, EditorData, Hotkeys
from anim import Tutorial, EDITOR_TUTORIAL
from sys import stdout
from abc import ABC, abstractmethod

Data = TypeVar("Data")

@dataclass(slots=True)
class EndlessData:

    spike_trials: int = 1
    mountain_of_asterisks: int = 1

    def __post_init__(self):

        if not (isinstance(self.spike_trials, int)
                and isinstance(self.mountain_of_asterisks, int)
        ):
            raise ValueError("Did not receive integers for data.")

        if self.spike_trials < 1 or self.mountain_of_asterisks < 1:
            raise ValueError("Received integer less than 1 for data.")

    def __repr__(self):

        return "EndlessData(spike_trials={}, mountain_of_asterisks={})".format(
            self.spike_trials,
            self.mountain_of_asterisks
        )

    @classmethod
    def from_tuple(cls, t: tuple):

        return EndlessData(*t)

    def view(self):

        clear()

        str_list = [
            f"Spike Trials: Level {self.spike_trials}",
            f"Mountain of Asterisks: Level {self.mountain_of_asterisks}"
        ]

        stdout.write(StringUtils.bar(str_list) + "\n")
        IOUtils.input("Press [ENTER] to continue. ")

    @property
    def endless_score(self):

        return (self.spike_trials - 1) + \
            2 * (self.mountain_of_asterisks - 1)

class EndlessPlayer:

    def __init__(self, mode: Literal[1, 2], icon: str="O",
                 display_coords: bool=False, display_percentage: bool=True):

        self.mode = mode
        self.icon = icon
        self.display_coords = display_coords
        self.display_percentage = display_percentage

        self.parameters = GenerationParameters.from_mode(mode)

    def play(self, initial_data: LevelData=None):

        clear()

        total_jumps = 0

        first = True
        while True:

            if first:
                endless = Endless(self.parameters, icon=self.icon,
                                  _level_data=initial_data,
                                  display_coords=self.display_coords,
                                  display_percentage=self.display_percentage
                                  )
                first = False
            else:
                endless = Endless(self.parameters, icon=self.icon,
                                  display_coords=self.display_coords,
                                  display_percentage=self.display_percentage
                                  )

            status, jumps = endless.play()

            total_jumps += jumps

            if status.result == Result.NONE:
                break

            self.parameters = next(self.parameters)

        return self.parameters.level, total_jumps

class _EndlessMode:

    def __init__(self, endless_mode: EndlessMode):

        self.endless_mode = endless_mode

        self.data = {
            n: Endless(GenerationParameters.from_mode(n))._level_data.copy()
            for n in (1, 2)
        }

    def score_from_mode(self, mode):

        if mode == 1:
            return self.endless_mode.data.endless_data.spike_trials
        elif mode == 2:
            return self.endless_mode.data.endless_data.mountain_of_asterisks

    def gui(self, mode):

        lines = [
            "Choose mode using [a/d], [ENTER] to select, [x] to exit: "
        ]

        lines.append(str(self.data[mode].map)[:-1])
        options = ["Spike Trials", "Mountain of Asterisks"]
        for _mode in self.data:

            option = options[_mode - 1]

            options[_mode - 1] = (
                f"> {option} <" if _mode == mode else f"  {option}  "
            )

        options_str = StringUtils.distribute(options, width=(Constants.X_LEN - 2))

        lines.extend([
            f"| {options_str} |",
            "~" * (Constants.X_LEN + 2),
            "-> "
        ])

        return "\n".join(lines)

    def choose_mode(self):

        mode = 0
        n = len(self.data)

        while True:

            clear()

            stdout.write(self.gui(mode + 1))
            selection = IOUtils.input(sanitize=True)

            match selection.strip().lower():

                case "a":
                    mode = (mode - 1) % n
                case "d":
                    mode = (mode + 1) % n
                case "":
                    return mode + 1
                case "x":
                    return - 1

    def run(self):

        mode = self.choose_mode()

        if mode != - 1:

            current_score = self.score_from_mode(mode)
            score, jumps = EndlessPlayer(mode, self.endless_mode.icon,
                                         self.endless_mode.data.main_data.settings.display_coords,
                                         self.endless_mode.data.main_data.settings.display_percentage,
                                         ).play(self.data[mode])

            if score > current_score:

                if mode == 1:
                    self.endless_mode.data.endless_data.spike_trials = score
                elif mode == 2:
                    self.endless_mode.data.endless_data.mountain_of_asterisks \
                        = score

            self.endless_mode.total_jumps += jumps

class EndlessMode:

    def __init__(self, data: Data):

        self.data = data

        self.total_jumps = 0
        self.total_attempts = 0

    @property
    def icon(self):
        return self.data.main_data.icon

    @property
    def username(self):
        return self.data.main_data.username

    @property
    def gui(self):

        str_list = [
            "Play",
            "View Endless Mode Progress",
            "Info",
            "Exit"
        ]

        header = f"Endless Mode [{self.username}] [You are: {self.icon}]"

        return StringUtils.menu(header, str_list)

    def run(self):

        while True:

            clear()

            selection = IOUtils.input(self.gui, sanitize=True)

            match selection:

                case "1":

                    _EndlessMode(self).run()

                case "2":

                    self.data.endless_data.view()

                case "i":

                    InfoUtils.display_info("ENDLESS")

                case "x":

                    self.data.main_data.stats.jumps += self.total_jumps
                    self.data.main_data.stats.attempts += self.total_attempts

                    return self.data

class Progress(dict, ABC):

    """A dictionary that stores progress for levels.
    Maps level IDs to Status objects. This is an
    abstract method, meaning that it should only
    be used after it has been subclassed and a
    database has been assigned."""

    @property
    @abstractmethod
    def db(self):

        "DEFINE THIS IN SUBCLASSES"

    def __missing__(self, level_id: str):

        if level_id not in type(self).db:
            raise KeyError(f"ID {level_id} does not exist.")

        default_time = type(self).db.timelimit(level_id)

        return Status(Result.NONE, default_time)

    @property
    def score(self):

        db = type(self).db

        return sum(
            db[id].score(status.result)
            for id, status in self.items()
        )

    @property
    def coins(self):

        return sum(1 for x in self.values() if Result.COIN in x.result)

    def update_id(self, level_id: str, status: Status):

        if not (isinstance(status, Status) and isinstance(level_id, str)):
            raise ValueError("Received wrong value for status / level_id")

        if level_id == LevelData.NULL.id:
            return

        current_result, current_record = self[level_id]

        new_result, new_record = status

        if isnan(new_record) or len(new_result) < len(current_result):
            return

        if len(new_result) > len(current_result):
            self[level_id] = status
        elif new_record < current_record:
            self[level_id] = status

    def __repr__(self):

        cls_name = type(self).__name__

        lst = "{" + ", ".join(
            f"{type(self).db.title(level_id)!r}: {status}"
            for level_id, status in self.items()
        ) + "}"

        return f"{cls_name}({lst})"

class CustomData(Progress): # User's progress on public levels.

    db = PUBLIC_DATABASE

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    @property
    def custom_score(self):
        return self.score

class LevelController:

    def __init__(self, custom_mode: CustomMode):

        self.custom_mode = custom_mode

    def create_new_level(self):

        level_data = EditorMode(hotkeys=self.custom_mode.hotkeys).edit()

        if level_data == LevelData.NULL:
            return

        save = IOUtils.get_validation(
            "Do you want to save this level? [Yes or no.] "
        )

        if save == IOUtils.Response.NO:
            return

        level_data.author = self.custom_mode.data.main_data.username
        self.custom_mode.editor_data.append(level_data)

    def load_save_str(self):

        clear()
        stdout.write("""Paste a save string of a level!
These save strings come from the level editor, and they allow you
to share and store created levels.\n"""
                     )

        string = IOUtils.input("Paste save string here: ")
        clear()

        try:
            level_data = LevelData.from_save_str(string)
        except Exception:

            clear()
            stdout.write("Invalid save string.\n")
            IOUtils.input("Press [ENTER] to continue. ")
            return

        self.custom_mode.editor_data.append(level_data)

        stdout.write(
            f"'{level_data.title}' has been added to your collection!\n"
        )

        sleep(2)

    def _created_levels(self, ind, level_data):

        while True:

            clear()

            stdout.write("\n".join(
                (
                    f"You selected: '{level_data.title.upper()}'",
                    StringUtils.distribute(
                        ["[1] Play Level", "[2] Edit Level"], width=(Constants.X_LEN + 2)),

                    StringUtils.distribute(
                        ["[3] Delete Level", "[4] Save String"], width=(Constants.X_LEN + 2)),
                    str(level_data.map),
                )
            ))

            selection = IOUtils.input(
                "Select a number, press [x] to exit: ",
                sanitize=True
            )

            match selection.strip().lower():

                case "1":

                    LoadUtils.load(level_data)

                    *_, new_jumps = Platformer(
                        level_data,
                        icon=self.custom_mode.data.main_data.icon,
                        display_desc=self.custom_mode.data.main_data.settings.display_desc,
                        display_coords=self.custom_mode.data.main_data.settings.display_coords,
                        display_percentage=self.custom_mode.data.main_data.settings.display_percentage,
                    ).play()

                    self.custom_mode.total_attempts += 1
                    self.custom_mode.total_jumps += new_jumps

                case "2":

                    level_data = EditorMode(
                        level_data, hotkeys=self.custom_mode.hotkeys).edit()

                    if not level_data:
                        return ind

                    self.custom_mode.editor_data[ind] = level_data.copy()

                case "3":

                    confirmation = IOUtils.get_validation(
                        "Are you sure you want to delete? ")

                    if confirmation == IOUtils.Response.YES:
                        del self.custom_mode.editor_data[ind]

                    return 0

                case "4":

                    save_str = level_data.as_save_str()
                    clear()
                    stdout.write("""Level save strings provide a way
to share your own levels with others! You can copy paste this string
and others can load it to play your level!\n""")

                    stdout.write("Your save string is below.\n")
                    stdout.write(save_str + "\n")

                    IOUtils.input("Press [ENTER] to continue. ")

                case "x":

                    return ind

    def created_levels(self):

        start_ind = 0

        while True:

            if not self.custom_mode.editor_data:
                return

            clear()

            ind, level_data = self.custom_mode.editor_data.get_map(
                ind=start_ind)

            if ind is None:
                return

            start_ind = self._created_levels(ind, level_data)

class PublicLevelViewer:

    DESCS = {
        0: "Play the best user-created levels.",
        1: "Search for a specific user-created level.",
        2: "Browse all user-created levels.",
        3: "Go back."
    }

    def __init__(self, custom_mode: CustomMode):

        self.custom_mode = custom_mode
        self.index = 0

    @property
    def gui(self):

        desc = f"Description: {PublicLevelViewer.DESCS[self.index]}"

        lines = [
            "[>] Showcase",
            "[>] Search",
            "[>] Browse Levels",
            "[>] Exit"
        ]

        new = ["Public Levels: Choose an option."]

        for i, line in enumerate(lines):

            arrow = " <" if i == self.index else "  "

            new.extend([
                "~" * Constants.X_LEN,
                f"| {line:<{Constants.X_LEN - 6}}{arrow} |"
            ])

        new.extend([
            "~" * Constants.X_LEN,
            f"| {desc:<{Constants.X_LEN - 4}} |",
            "~" * Constants.X_LEN,
            "[w]/[s] to scroll, [Enter] to select: "
        ])

        return "\n".join(new)

    def play_level(self, level_data: LevelData, /):

        level_id = level_data.id

        current_record = self.custom_mode.data.custom_data[level_id].time

        # Edit record.
        loading_data = level_data.copy()
        loading_data.time = current_record

        LoadUtils.load(loading_data)

        new = Platformer(level_data, icon=self.custom_mode.icon,
                         display_desc=self.custom_mode.data.main_data.settings.display_desc,
                         display_coords=self.custom_mode.data.main_data.settings.display_coords,
                         display_percentage=self.custom_mode.data.main_data.settings.display_percentage,
                         ).play()

        new_status, new_jumps = new

        self.custom_mode.total_jumps += new_jumps
        self.custom_mode.total_attempts += 1

        self.custom_mode.data.custom_data.update_id(level_id, new_status)

    def showcase(self):

        ind, level_data = PaginateUtils.paginate(
            SHOWCASE_DATABASE, header="Play user-created levels!"
        )

        if ind is None:
            return

        self.play_level(level_data)

    def search(self):

        search = IOUtils.input("Level to search: -> ")

        matches = PUBLIC_DATABASE.query(search)

        if matches:

            ind, level_data = PaginateUtils.paginate(matches, header="Results:")

            if ind is None:
                return

            self.play_level(level_data)
        else:
            stdout.write("No results found.")
            IOUtils.input("Press [ENTER] to continue. ")

    def browse(self):

        ind, level_data = PaginateUtils.paginate(PUBLIC_DATABASE, header="Play user-created levels!")

        if ind is None:
            return

        self.play_level(level_data)

    def view(self):

        n = len(PublicLevelViewer.DESCS)

        while True:

            clear()

            stdout.write(self.gui)
            selection = IOUtils.input(sanitize=True)

            match selection:

                case "d" | "w":

                    self.index = (self.index - 1) % n

                case "a" | "s":

                    self.index = (self.index + 1) % n

                case "":

                    match self.index:

                        case 0:
                            self.showcase()

                        case 1:
                            self.search()

                        case 2:
                            self.browse()

                        case 3:
                            return

class HotkeyEditor:

    HOTKEY_TEMPLATE = """
~~~~~~~~~~~        ~~~~~~~~~~~
|         |        |         |
|         |        |         |
|    a    | =====> |    b    |
|         |        |         |
|         |        |         |
~~~~~~~~~~~        ~~~~~~~~~~~"""[1:]

    def __init__(self, hotkeys: Hotkeys):

        self.hotkeys = hotkeys

        self._order = list(hotkeys)

    @classmethod
    def hotkey_str(cls, hotkey: str, character: str):

        return cls.HOTKEY_TEMPLATE.replace("a", hotkey).replace("b", character)

    def gui(self, index: int):

        header = "Edit hotkeys."
        footer = "[w]/[s]: scroll, [Enter]: select, 'exit': exit, [i]: info"

        gui = list()
        gui_length = len(footer)

        gui.append(header)

        hotkey_lst = [
            "| {}{}{} {} |".format(
                hotkey,
                " " * (gui_length - 8),
                self.hotkeys[hotkey],
                "<" if i == index else " "
            )

            for i, hotkey in enumerate(self._order)
        ]

        hotkey_lst.append(
            "| + New {} {} |".format(
                " " * (gui_length - 12),
                "<" if index == len(self.hotkeys) else " "
            )
        )

        div = "~" * gui_length
        hotkey_str = f"\n{div}\n".join(hotkey_lst)

        gui.extend([div, hotkey_str, div, footer, "-> "])

        return "\n".join(gui)

    def edit(self, index: int):

        hotkey = self._order[index]

        string = f"What character would you like to assign the '{hotkey}' hotkey?"

        while True:

            clear()
            stdout.write(string + "\n")

            char = IOUtils.input(f"{hotkey} -> ", sanitize=True)

            if char == "exit":
                return

            if len(char) != 1:
                string = "Invalid character. Try again."
                continue
            elif char not in Hotkeys.POSSIBLE_CHARS:
                string = "Shortcut not available for that character. Try again."
                continue
            elif char in self.hotkeys.values():
                string = \
                    "A shortcut for that character already exists. Try again."
                continue

            self.hotkeys[hotkey] = char
            break

    def delete(self, index: int):

        hotkey = self._order[index]

        clear()

        # Confirm
        stdout.write(f"Deleting hotkey: {hotkey} -> {self.hotkeys[hotkey]}\n")

        confirm = IOUtils.get_validation(
            "Are you sure you want to delete? [y/n] "
        )

        if confirm == IOUtils.Response.YES:
            del self.hotkeys[hotkey]
            del self._order[index]

    def new(self):

        string = "Type in a hotkey. Must be alphabetic [a-z]."

        while True:

            clear()
            stdout.write(string + "\n")

            hotkey = IOUtils.input("-> ", sanitize=True)

            if hotkey == "exit":
                return

            if len(hotkey) != 1:
                string = "Invalid hotkey. Try again."
                continue
            elif hotkey not in Hotkeys.POSSIBLE_KEYS:
                string = "That hotkey is not available. Try again."
                continue
            elif hotkey in self.hotkeys:
                string = "That hotkey is already being used. Try again."
                continue

            break

        string = f"What character would you like to assign the '{hotkey}' hotkey?"

        while True:

            clear()
            stdout.write(string + "\n")

            char = IOUtils.input(f"{hotkey} -> ", sanitize=True)

            if char == "exit":
                return

            if len(char) != 1:
                string = "Invalid character. Try again."
                continue
            elif char not in Hotkeys.POSSIBLE_CHARS:
                string = "Shortcut not available for that character. Try again."
                continue
            elif char in self.hotkeys.values():
                string = \
                    "A shortcut for that character already exists. Try again."
                continue

            self.hotkeys[hotkey] = char
            self._order.append(hotkey)
            break

    def edit_or_delete(self, index: int):

        while True:

            hotkey = self._order[index]
            character = self.hotkeys[hotkey]

            hotkey_str = HotkeyEditor.hotkey_str(hotkey, character)

            clear()

            stdout.write("Selected: \n")
            stdout.write(hotkey_str + "\n")
            stdout.write("[1] Edit [2] Delete [x] Exit\n")

            x = IOUtils.input("-> ", sanitize=True)

            match x:

                case "1":

                    self.edit(index)

                case "2":

                    self.delete(index)
                    return

                case "x":
                    return

    def run(self):

        index = 0

        while True:

            hotkeys = self._order + ["New"]

            clear()
            stdout.write(self.gui(index))

            x = IOUtils.input(sanitize=True)

            match x:

                case "s":
                    index += 1
                case "w":
                    index -= 1
                case "":

                    i = hotkeys[index]
                    if i == "New":
                        self.new()
                    else:
                        self.edit_or_delete(index)

                case "i":

                    InfoUtils.display_info("HOTKEYS")
                case "exit":
                    return self.hotkeys

            index %= len(hotkeys)

class CustomMode:

    def __init__(self,
                 data: Data,
                 hotkeys: Hotkeys,
                 editor_data: EditorData=None):

        if editor_data is None:
            editor_data = EditorData()

        self.total_jumps = 0
        self.total_attempts = 0

        self.data = data
        self.editor_data = editor_data
        self.hotkeys = hotkeys

        self.icon = data.main_data.icon
        self.username = data.main_data.username

        self.level_controller = LevelController(self)
        self.public_level_viewer = PublicLevelViewer(self)
        self.hotkey_editor = HotkeyEditor(self.hotkeys)

    @property
    def gui(self):

        str_lst = [
            "Create New Level",
            "Created Levels",
            "Load Save String",
            "Public Levels",
            "Editor Tutorial",
            "Edit Hotkeys",
            "Info",
            "Exit"
        ]

        no_levels1 = "" if self.editor_data else "(No levels created yet!)"
        no_levels2 = "" if self.editor_data else "(!)"

        subs = {0: no_levels2, 1: no_levels1}

        header = f"Custom Level Mode [{self.username}] [You are: {self.icon}]"
        return StringUtils.menu(header, str_lst, subs=subs)

    def run(self):

        while True:
            clear()

            selection = IOUtils.input(self.gui, sanitize=True)

            match selection:

                case "1": # Create a level.

                    self.level_controller.create_new_level()

                case "2": # Created levels.

                    self.level_controller.created_levels()

                case "3": # Load Save String

                    self.level_controller.load_save_str()

                case "4":

                    self.public_level_viewer.view()

                case "5":

                    Tutorial(EDITOR_TUTORIAL).run()

                case "6":

                    self.hotkeys = self.hotkey_editor.run()

                case "i":

                    InfoUtils.display_info("CUSTOM")

                case "x":
                    break

        self.data.main_data.stats.jumps += self.total_jumps
        self.data.main_data.stats.attempts += self.total_attempts

        return self.data, self.editor_data

class PackMode:

    def __init__(self, data: Data):

        self.data = data

    # --- Formatting ---
    @property
    def gui(self):

        header = "Experimental Level Packs [{}] [You are: {}]".format(
            self.data.main_data.username,
            self.data.main_data.icon
        )

        str_lst = list(PACKS.values())
        str_lst.extend(["View Progress", "Info", "Exit"])

        return StringUtils.menu(header, str_lst)

    def view_progress(self):
        self.data.main_data.progress.view(PACK_RANGE)

    # --- End ---

    def play_range(self, r: range):

        if r in PACKS: # packs is now a dict of {range: name}.

            db = LevelDatabase.from_range(r)

            ind, level = PaginateUtils.paginate(db)

            if ind is None:
                return

            LoadUtils.load(level)

            status, jumps = Platformer(level, icon=self.data.main_data.icon,
                                       display_desc=self.data.main_data.settings.display_desc,
                                       display_coords=self.data.main_data.settings.display_coords,
                                       display_percentage=self.data.main_data.settings.display_percentage,
                                       ).play()

            self.data.main_data.progress.update_id(level.id, status)

            self.data.main_data.stats.jumps += jumps
            self.data.main_data.stats.attempts += 1

    def run(self): # Adaptive.

        num_to_range = dict(enumerate(list(PACKS), 1))
        view_progress = max(num_to_range) + 1

        while True:
            clear()
            stdout.write(self.gui)

            i = IOUtils.input()

            match i:

                case i if i.isdigit():
                    i = int(i)

                    if i == view_progress:
                        self.view_progress()

                    r = num_to_range.get(i, None)

                    if r is None:
                        continue

                    self.play_range(r)

                case "i":

                    InfoUtils.display_info("PACKS")

                case "x":
                    return self.data
