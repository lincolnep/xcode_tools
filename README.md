# Xcode Tools

This tool downloads the latest Xcode CLI Tools and two supporting SDK packages to your desktop.

These tools are usually behind the Apple Developer portal, and come in a DMG file containing a single pkg installer.

## Usage
1. `git clone https://github.com/carlashley/xcode_tools && cd xcode_tools`
2. `chmod +x xcode_tools.py`
3. `./xcode_tools.py`
4. ``???``
5. `Profit`

## Test
The three packages downloaded by this script (as at 2017-04-10) install without errors on a system without Xcode installed, however I don't really use the Xcode CLI tools for much more than `git`, so if anyone happens to use other tools, could you please test to ensure it works the way as expected?

## Why not just run  `xcode-select --install` ??
Because any opportunity to avoid pesky GUI dialog boxes is one worth taking!
