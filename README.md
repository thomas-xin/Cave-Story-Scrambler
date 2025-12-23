# Cave-Story-Scrambler
A text scrambler for the game Cave Story. Works with the vanilla game, as well as mods that do not modify the TSC parser. By default, additionally converts all TSC files into an intermediate format readable as both TSC and TXT, patching executable's parser to allow this special representation.

## Usage
The script may be run as part of a mod, by taking the following steps:
- Copy `scramble.exe`, as well as optionally `dictionary.txt` (if a full dictionary of words is intended, rather than only existing words from the game), into the Cave Story folder's main directory (same as Doukutsu.exe).
- Run `scramble.exe`, which should create a patched copy of the game folder, and automatically run the game afterwards.
    - The original game folder and all its contents will *not* be modified.

### Advanced
Alternatively, one may run the script as a standalone program (e.g. as a TSC linebreak fixer), with the following arguments:
```python
usage: scramble [-h] [-V] [-sr SCRAMBLE_RATE] [-f | --force | --no-force]
                [-tc | --text-compatible | --no-text-compatible] [-r | --run | --no-run]
                game_folder

Cave Story dialogue scrambler

positional arguments:
  game_folder           Top level directory of folder to process. Output will be a copy of this folder with the "~"
                        character appended.

options:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -sr, --scramble-rate SCRAMBLE_RATE
                        Chance for each word to be scrambled; defaults to 0.1
  -f, --force, --no-force
                        Forces at least one change per TSC event; defaults to TRUE
  -tc, --text-compatible, --no-text-compatible
                        Forces output to be both TSC and TXT compliant; defaults to TRUE
  -r, --run, --no-run   Immediately run the game after patching; defaults to FALSE
```

## Credits
https://github.com/first20hours/google-10000-english for included dictionary