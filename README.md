# Aggressive DSE

Aggressive DSE is a Binary Ninja helper plugin that opts every variable written
in HLIL into dead-store elimination. It repeats analysis until no additional
written variables appear, or until a safety limit of ten passes is reached.

## Installation

Clone or copy this repository into your Binary Ninja user plugins directory as
an `aggressive_dse` folder, then restart Binary Ninja:

- macOS: `~/Library/Application Support/Binary Ninja/plugins/aggressive_dse`
- Linux: `~/.binaryninja/plugins/aggressive_dse`
- Windows: `%APPDATA%\Binary Ninja\plugins\aggressive_dse`

## Usage

Choose **Aggressive DSE → Current Function** or **Aggressive DSE → Entire
Binary** from the command palette or Plugins menu. Work runs as a cancellable
background task, with progress and results sent to Binary Ninja's log.

## Caveat

This deliberately overrides Binary Ninja's default DSE choice for every
written variable it discovers. This can make decompilation cleaner, but may
hide writes useful during manual analysis. Save or duplicate your database
before applying it broadly if you want an easy way back.

## Development

Run the dependency-free tests with `python3 -m unittest discover -s tests`.

## License

MIT
