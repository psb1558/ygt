# Ygt

**Ygt** is a Python app for hinting TrueType fonts. It is built to be fast, flexible, and free:

- it will run equally well under Windows, Mac OS, and Linux;
- it emphasizes modern requirements for TrueType hinting while deemphasizing the obsolete;
- the most common commands use unmodified shortcut keys so you can work quickly with one hand on the keyboard and one on the mouse;
- it will read either a TrueType font or a UFO;
- it can save hints in an easily understood and edited YAML file,
- which can be compiled to a hinted font either from inside the program or from the command line,
- or it can save compiled hints to a UFO (from which fontmake can produce a hinted font)

Ygt is in an alpha state, with features yet to be added (especially auto-hinting). But it is already a workable program, which the developer has used to hint thousands of glyphs in several large fonts.

For the time being, Ygt must be launched from a command line. To install, make sure you are running Python 3.10.4 or later and type `pip install ygt` on the command line. Alternatively, download the files from GitHub, navigate to the directory with the file pyproject.toml, and type `pip install .` (don't forget the period!). Then type `ygt` on the command line to start the program.

For more information, see the [documentation](https://github.com/psb1558/ygt/tree/main/docs) or watch a brief [introductory video](https://psb1558.github.io/ygt/index.html).

## Changes

### Version 0.1.24 (2023-4-19)

When we read a UFO, we do not rename glyphs. This prevents incompatibilities between in-memory font and font on disk, and it simplifies export. However, it may complicate shifting back and forth between UFO and YAML modes.

Ygt sometimes hung when summoning a Font View window for fonts read from UFO. This is now fixed.

Program now (partly) honors dark themes on various platforms.

### Version 0.1.23 (2023-4-17)

changes three keywords in Ygt’s YAML-based hinting language: `blackspace`, `whitespace`, and `grayspace` become `blackdist`, `whitedist`, and `graydist`. If you have created a hinting file for earlier versions, run this sed script:
```
s/blackspace/blackdist/g
s/whitesapce/whitedist/g
s/grayspace/graydist/g
```
Among other changes intended to improve stability, this version consolidates various font-level edits in a “Font Info” dialog, summoned with Ctrl-I or Cmd-I, and honors “dark themes” on various platforms.
