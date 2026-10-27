# 🧪 MixaPozioni

🇮🇹 [Versione italiana](README_it.md)

An educational game for primary-school children (ages 6-10): mix colourful potions
in a cauldron and discover how secondary colours are made.
The game's interface is entirely in Italian.

![Paint](docs/screenshot_pittura.png)
![Light](docs/screenshot_luce.png)

---

## 1. For teachers

1. **Download** the file (`MixaPozioni.exe` for Windows, `MixaPozioni-Mac.zip` for Mac).
2. **Double-click** to open it. Nothing needs to be installed.

**Windows** – if the blue "Windows protected your PC" warning appears, click
**"More info"** → **"Run anyway"**. (It shows up because the program is new and unsigned, not because it is dangerous.)

**Mac** – unzip the file, then **right-click** MixaPozioni → **Open** → **Open**.

**How to play:** click the potions to drop doses into the cauldron and read the name
of the colour you get. "Svuota" (Empty) starts over. "Pittura" (Paint) and "Luce" (Light)
switch the way colours mix. **F11** = full screen, **M** = mute. **ESC** never closes the
game straight away: it asks for confirmation first.

---

## 2. For developers

### Setup and run
Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
python main.py
```

### Tests
```bash
python -m pytest -q
```
`tests/test_color_mixing.py` tests colour mixing and colour names (pure functions);
`tests/test_smoke.py` runs the whole game headless (SDL `dummy` drivers) and simulates
clicks, mode switching, emptying, ESC and window resizing. The same script
(`tools/smoke_test.py`) regenerates the screenshots in `docs/`.

### Building the executable
| System | Command | Output |
|---|---|---|
| Windows | `build_windows.bat` | `dist\MixaPozioni.exe` |
| Mac | `./build_mac.sh` | `dist/MixaPozioni.app` |
| Linux | `./build_linux.sh` | `dist/MixaPozioni` |

The scripts create a venv, install the dependencies and run PyInstaller
(`--onefile --windowed`; on Mac `--onedir --windowed`, see below).

### Getting the .exe without a Windows machine (GitHub Actions)
1. Push the project to a GitHub repository on `main`
   (or go to *Actions → Build MixaPozioni → Run workflow*).
2. The workflow `.github/workflows/build.yml` runs the tests and builds on
   Windows, macOS and Linux.
3. When the run finishes, open its page and download the files from the **Artifacts**
   section: `MixaPozioni-Windows` (contains the `.exe`), `MixaPozioni-Mac`, `MixaPozioni-Linux`.

### Project structure
```
main.py                 entry point (DPI awareness, error log to file)
game/constants.py       layout, themes, resource_path() for PyInstaller (sys._MEIPASS)
game/color_mixing.py    Paint (RYB) and Light (RGB) mixing, pure functions
game/color_names.py     Italian colour names (separate tables per mode)
game/entities.py        potions, cauldron, drops, particles, dose counters
game/ui.py              fonts, hand-drawn icons, buttons, mode selector
game/audio.py           numpy-synthesised sounds + silent fallback
game/game.py            main loop, states, scaling, events
```

### Technical decisions
- **Paint = RYB model with trilinear interpolation.** The 3 primaries (R, Y, B) are
  coordinates in the RYB cube; its 8 corners are mapped to hand-picked RGB colours
  (derived from the classic Gosset-Chen cube but more vivid: the original blue is too dull
  for children). Doses are **normalised by dividing by the largest one**, so
  1R+1Y and 4R+4Y give the same saturated orange (without normalising, white would be
  mixed in and the result would look washed out). Equal parts of R+Y+B give brown.
  A "physical" subtractive mix (Kubelka-Munk) was discarded: with school RYB primaries
  it produces greens and purples that are hard to recognise.
  RYB was chosen because it is what is taught in school; strictly speaking, the
  subtractive primaries are cyan, magenta and yellow.
- **Light = additive RGB sum** using the same normalised proportions; equal parts
  of R, G, B give white. Dark background, dark cauldron and a glowing halo.
- **Colour names**: nearest name in CIE Lab space among 12 names (Paint) and 13 (Light:
  including White, Magenta, Cyan, Yellow). Difficult names are avoided.
- **Maximum 10 doses**, counting those still falling; beyond that the flask shakes
  and a "Pieno!" (Full) speech bubble appears (no errors or harsh sounds).
- **Switching mode** empties the cauldron instantly; **"Svuota"** plays an animation
  (the cauldron tilts and pours).
- **Scaling**: fixed 1024×768 logical surface scaled to the window with black bars.
  On small screens the initial window shrinks while keeping the aspect ratio.
- **Full screen**: F11, F, or the button at the top; **ESC** leaves full screen, and in
  windowed mode asks for confirmation ("Vuoi uscire?"). The window's X closes immediately.
- **Fonts**: first available among Comic Sans, Trebuchet, Verdana, Segoe UI, DejaVu,
  Arial; otherwise the font bundled with pygame. No font is distributed.
- **Graphics/audio**: zero external assets. Static parts (flasks, cauldron, backgrounds)
  are precomputed with supersampling; particles shrink instead of using alpha to keep
  60 FPS on old PCs. Sounds are synthesised with numpy; without an audio device the
  game still starts, silently.
- **Touch**: touchscreens generate mouse events (SDL default), so no dedicated code is
  needed. Click areas on potions are enlarged by 22 px.
- **macOS**: PyInstaller discourages `--onefile` with `--windowed` (deprecated), so
  `--onedir --windowed` is used, which still produces a single `.app`. Being unsigned,
  it needs right-click → Open on first launch.
- **Errors**: if the game crashes at startup it writes `MixaPozioni_errore.txt` in the
  user's home folder (there is no console with `--windowed`).
- The jingle and sparkles fire when, after mixing at least 2 primaries, the colour
  name changes.
