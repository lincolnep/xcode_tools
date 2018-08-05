# Xcode Tools

This tool downloads the latest Xcode CLI Tools and two supporting SDK packages to your desktop.
**Note** Pay careful attention to the packages downloaded, as it will find _all_ matching Xcode CLI related installers.

These tools are usually behind the Apple Developer portal, and come in a DMG file containing a single pkg installer.

## Usage
1. `git clone https://github.com/carlashley/xcode_tools && cd xcode_tools`
1. `chmod +x xcodetools.py`
1. `./xcodetools.py --help`
1. ``???``
1. `Profit`

## What this does
This utility parses the Software Update catalog for specific macOS versions (if none provided, defaults to your version of macOS), finds the XCode Command Line Tools and SDK files (or all those applicable), and downloads them.

This can also be used to install the tools.

If no arguments are provided, the default behaviour is to download the Command Line Tools and SDK (if available) for the release of macOS the script is run on.

## Why not just run  `xcode-select --install` ??
Because any opportunity to avoid pesky GUI dialog boxes is one worth taking!
