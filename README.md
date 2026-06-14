# ASCII Ascent

A terminal-based ASCII platformer game.

```
  m   .m,   mm  mmm  mmm        m   .m,   mm .mmm,.m .,.mmm,
 ]W[ .P'T  W''[ 'W'  'W'       ]W[ .P'T  W''[]P''`]W ][''W'`
 ]W[ ]b   ]P     W    W        ]W[ ]b   ]P   ][   ]P[][  W
 W W  TWb ][     W    W        W W  TWb ][   ]WWW ][W][  W
 WWW    T[]b     W    W        WWW    T[]b   ][   ][]d[  W
.W W,]mmd` Wmm[ mWm  mWm      .W W,]mmd` Wmm[]bmm,][ W[  W
'` '` ''`   ''  '''  '''      '` '` ''`   '' ''''`'` '`  '
```

## Requirements

- Python 3.12+ (uses `itertools.batched`, `kw_only` dataclasses, `Self`, PEP 695 generics)
- No third-party dependencies — standard library only

## Run

```
python main.py
```

- To start from a save string, paste it into `SAVESTR` at the top of [main.py](main.py).
- Or, go to the in-game 'Load Game' option in the main menu and paste the save string
  into the terminal.

## Modes

- **Play** — work through the main level progression, ending in the Tower.
- **Creator** — build, save, and play your own levels with the in-game editor.
- **Endless** — auto-generated levels for score chasing (Spike Trials and
  Mountain of Asterisks).
- **Level Packs** — additional level collections, unlocked after beating the
  Tower.
- **Tutorial** — interactive walkthroughs of platformer controls and the level
  editor.
- **Account** — view progress, achievements, statistics, and settings.

## Save / Load

The game has no on-disk save file. From the main menu, **Save** prints a save
string you can copy; paste it back into `SAVESTR` (or at startup) to restore
progress. Levels you create in the editor are shared the same way — each level
has its own save string for sharing or backup.

Save string format: pickled data → zlib compression → base85 encoding. Plain
text, single-line, transport-safe.

## Architecture

The codebase is organized by layer:

| File | Layer | Role |
| --- | --- | --- |
| [main.py](main.py) | Entry | Boot, optional `SAVESTR` |
| [mainmode.py](mainmode.py) | Controller | Main menu, account viewer, level player |
| [othermodes.py](othermodes.py) | Controller | Custom, Endless, Pack, and Showcase modes |
| [editormode.py](editormode.py) | Controller | Level editor, hotkey system, commands |
| [plat.py](plat.py) | Runtime | Platformer engine (`Platformer`, `Tower`, `Endless`) |
| [anim.py](anim.py) | Runtime + data | Cutscenes (`CutsceneData` / `Cutscene`) and tutorials (`TutorialData` / `Tutorial`) |
| [maps.py](maps.py) | Data | `LevelData`, `GameMap`, `LevelDatabase`, `Charset`/`Charseq`, `Coordinates`, embedded levels |
| [utils.py](utils.py) | View | Formatting, I/O, loading animations, `paginate` |
| [clear.py](clear.py) | View | Cross-platform terminal clear |

### Model / View separation

The model layer (`maps.py`, data classes in `anim.py`) is pure data — no
`stdout`, no `IOUtils`, no presentation logic. Runtime wrappers
(`Platformer`, `Cutscene`, `Tutorial`) carry player context (icon, username) and
own all rendering. This keeps the data classes serialization-clean and the
runtime classes testable in isolation.

### Character sets

Map glyphs are typed through the `Charset` (unordered) and `Charseq` (ordered)
abstractions in `maps.py`, validated against a shared `MAP_UNIVERSE`. Keyboard
input keys go through a separate `Lowercase` charset. The discipline prevents
runtime-derived characters (`Map.NAC` for out-of-bounds reads) from leaking
into user-facing palettes.

### Coordinate system

Player coordinates have y=0 at the **bottom**, matching the platformer's
gravity convention. `GameMap` storage matches this — `self.map[0]` is the floor
row. The visual terminal output reverses this in `__format__` only; everywhere
else the convention is consistent.

## Development

Embedded data (level save strings, cutscene save strings, tutorial save strings)
lives at the top of `maps.py` and `anim.py` as module constants. The classes
that parse and operate on this data follow below, then runtime wrappers at the
bottom.

To add a new level: build it in the editor, copy the level save string,
paste it into the appropriate `*_STRS` constant.

To add a new cutscene or tutorial: construct the data in Python, call
`as_save_str()` on it, paste the result into the source as a `*_STR` constant.

## Version

`__version__` is defined in [main.py](main.py).
