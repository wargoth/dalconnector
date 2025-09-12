# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DAL Connector is an Ableton Live control surface script that connects a Synthstrom Deluge to Ableton Live 11. It enables automatic synchronization of Deluge song files from a WiFi SD card (like Toshiba Flashair) to Ableton Live tracks.

## Architecture

The codebase consists of several core modules:

### Core Components

- **DALConnector.py**: Main control surface class that extends Ableton's `ControlSurface`. Handles track selection, song loading, and event management.
- **fetcher.py**: Network communication layer with two main classes:
  - `Fetcher`: Background thread that polls the WiFi SD card for song files
  - `ThreadShare`: Thread-safe communication interface between fetcher and main thread
- **usb_fetcher.py**: USB SysEx communication layer with two main classes:
  - `USBFetcher`: Background thread that communicates with Deluge over USB using MIDI SysEx protocol
  - `USBThreadShare`: Thread-safe communication interface for USB connection
- **deluge2ableton.py**: Converter that parses Deluge XML song files and transforms them into Ableton-compatible note data
- **local.py**: Utility functions for song name formatting and display
- **config.py**: Configuration file for connection method and settings

### Data Flow

#### USB Connection (Default)
1. User names an Ableton track with "dc:" prefix followed by song number (e.g., "dc:4a")
2. DALConnector detects track name change and requests song from USB fetcher
3. USB fetcher sends MIDI SysEx commands to Deluge to open and read XML file (SONG004A.XML)
4. XML data is received via SysEx response and parsed by Deluge2Ableton converter
5. Ableton tracks and clips are created/updated with the note data
6. Optionally watches for subsequent saves (4b, 4c, etc.) and auto-loads them

#### WiFi Connection (Legacy)
1. User names an Ableton track with "dc:" prefix followed by song number (e.g., "dc:4a")
2. DALConnector detects track name change and requests song from WiFi fetcher
3. Fetcher polls WiFi SD card for corresponding XML file (SONG004A.XML) via HTTP
4. XML is parsed by Deluge2Ableton converter into clip/note data
5. Ableton tracks and clips are created/updated with the note data
6. Optionally watches for subsequent saves (4b, 4c, etc.) and auto-loads them

### Key Features

- Automatic tempo extraction from Deluge BPM data
- Support for MIDI, Synth, and Kit instruments from Deluge
- Scene-based organization (Deluge sections become Ableton scenes)
- Probability-based note data preservation
- Background polling for new song versions

## Configuration

Key configuration in `config.py`:
- `CONNECTION_METHOD`: "USB" (default) or "WIFI" - selects connection method
- `WIFI_CARD_ADDRESS`: IP or hostname of WiFi SD card (only used when CONNECTION_METHOD is "WIFI")
- `WATCH_FOR_NEW_SAVES`: Whether to poll for incremental saves
- `NEW_SAVE_SLEEP_TIMER`: Timeout for polling new saves

## Dependencies

For USB connection:
- `python-rtmidi>=1.4.0` - MIDI interface library

Install with: `pip install python-rtmidi`

## Installation and Usage

This is an Ableton Live control surface script that should be placed in Ableton's "MIDI Remote Scripts" directory.

### Setup Instructions

1. Install dependencies: `pip install python-rtmidi`
2. Configure connection method in `config.py`:
   - For USB connection (default): Set `CONNECTION_METHOD = "USB"`
   - For WiFi card: Set `CONNECTION_METHOD = "WIFI"` and configure `WIFI_CARD_ADDRESS`
3. Select DALConnector as a control surface in Ableton preferences
4. For USB connection: Ensure Deluge is connected via USB and recognized as a MIDI device

### Usage

Name MIDI tracks with "dc:" prefix followed by song number to trigger automatic song loading from the Deluge (e.g., "dc:4a" loads SONG004A.XML).

## Development Notes

- USB connection requires `python-rtmidi` library; WiFi connection uses only Python standard library
- USB communication uses MIDI SysEx protocol with JSON-based file operations
- WiFi communication uses raw socket HTTP requests to WiFi SD card
- Threading model with background fetcher and main Ableton thread communication
- Regular expression parsing for both Deluge XML format and song name patterns
- Logging to Ableton's log.txt file for debugging
- USB implementation follows Deluge firmware SysEx specification with proper 7-bit to 8-bit data unpacking