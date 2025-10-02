# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DAL Connector is an Ableton Live control surface script that connects a Synthstrom Deluge to Ableton Live 11 via USB. It enables automatic synchronization of Deluge song files directly from the Deluge's SD card to Ableton Live tracks using MIDI SysEx communication.

## Architecture

The codebase consists of several core modules:

### Core Components

- **DALConnector.py**: Main control surface class that extends Ableton's `ControlSurface`. Handles track selection, song loading, event management, and SysEx message routing.
- **fetcher.py**: USB SysEx communication layer with two main classes:
  - `Fetcher`: Background thread that communicates with Deluge over USB using MIDI SysEx protocol
  - `ThreadShare`: Thread-safe communication interface between fetcher and main thread
- **deluge2ableton.py**: Converter that parses Deluge XML song files and transforms them into Ableton-compatible note data
- **local.py**: Utility functions for song name formatting and display
- **config.py**: Configuration file for settings

### Data Flow

1. User names an Ableton track with "dc:" prefix followed by song number (e.g., "dc:4a")
2. DALConnector detects track name change and requests song from fetcher via ThreadShare
3. Fetcher sends MIDI SysEx commands to Deluge to open and read XML file (SONG004A.XML)
4. Deluge responds with SysEx messages containing JSON metadata and 7-bit encoded file data
5. SysEx responses are routed through Ableton's MIDI listener to fetcher's `handle_sysex_response()` method
6. Fetcher unpacks 7-bit to 8-bit data and decodes XML
7. XML is parsed by Deluge2Ableton converter into clip/note data
8. Ableton tracks and clips are created/updated with the note data
9. Optionally watches for subsequent saves (4b, 4c, etc.) and auto-loads them

### Key Features

- Automatic tempo extraction from Deluge BPM data
- Support for MIDI, Synth, and Kit instruments from Deluge
- Scene-based organization (Deluge sections become Ableton scenes)
- Probability-based note data preservation
- Background polling for new song versions

## Configuration

Key configuration in `config.py`:
- `WATCH_FOR_NEW_SAVES`: Whether to poll for incremental saves (default: True)
- `NEW_SAVE_SLEEP_TIMER`: Timeout for polling new saves in seconds (default: 600)

## Dependencies

No external dependencies required! DALConnector uses Ableton Live's built-in MIDI SysEx handling.

## Installation and Usage

This is an Ableton Live control surface script that should be placed in Ableton's "MIDI Remote Scripts" directory.

### Setup Instructions

1. Copy DALConnector folder to Ableton's MIDI Remote Scripts directory
2. In Ableton Preferences > Link/Tempo/MIDI:
   - Set a Control Surface to "DALConnector"
   - Set Input to "Deluge" (or your Deluge's MIDI port name)
   - Set Output to "Deluge" (or your Deluge's MIDI port name)
3. Ensure Deluge is connected via USB and recognized as a MIDI device

### Usage

Name MIDI tracks with "dc:" prefix followed by song number to trigger automatic song loading from the Deluge (e.g., "dc:4a" loads SONG004A.XML).

## Development Notes

- Uses Ableton Live's native MIDI SysEx handling - no external dependencies required
- Communication uses MIDI SysEx protocol with JSON-based file operations (Deluge firmware spec)
- Threading model with background fetcher and main Ableton thread communication
- SysEx responses are routed via Ableton's `received_midi` listener callbacks
- Regular expression parsing for both Deluge XML format and song name patterns
- Logging to Ableton's log.txt file for debugging
- Implements proper 7-bit to 8-bit data unpacking per Deluge firmware specification
- Global SysEx interceptor ensures messages reach the control surface despite Ableton's filtering