

# DALConnector USB MIDI Configuration
# ====================================
# This version uses the DelugeWeb SysEx protocol to read song XML files
# directly from the Deluge's /SONGS/ directory via USB MIDI

# USB MIDI Configuration for Deluge
# The MIDI port name pattern to look for when connecting to the Deluge
# The Deluge typically shows up as "Deluge Port 3" for SysEx communication
# If your Deluge shows up with a different name, update this setting
DELUGE_MIDI_PORT_NAME = "Deluge Port 3"




# Once you've loaded a song, do you want DAL Connector to periodically check for new saves?
# I.e., you've loaded song 8.  Now it will watch for 8b.  Then 8c.  Then 8d.
# If it finds one, it will try to load it
WATCH_FOR_NEW_SAVES =  True   # True or False


# If we're watching for new saves, when do we give up?  If one doesn't appear in X seconds, assume one isn't coming
# so we don't have to poll the Deluge forever.
NEW_SAVE_SLEEP_TIMER = 600  # Integer seconds


# MIDI Communication Settings
# ===========================

# MIDI connection timeout in seconds
MIDI_TIMEOUT = 5

# SysEx Protocol for Deluge Communication
# ======================================
# Based on the DelugeWeb project implementation, the actual SysEx protocol is:
# 
# Deluge Manufacturer ID: 0x00, 0x21, 0x7B (Synthstrom Audible)
# Device ID: 0x01 (Deluge)
#
# Known command types:
# - 0x03: Debug/logging messages
# - 0x04: JSON-based commands
# - 0x05: JSON responses
#
# Protocol structure:
# [0xF0, 0x00, 0x21, 0x7B, 0x01, command_type, sequence_number, ...data..., 0xF7]

# Deluge SysEx command structure
DELUGE_MANUFACTURER_ID = [0x00, 0x21, 0x7B]  # Synthstrom Audible
DELUGE_DEVICE_ID = 0x01  # Deluge device
SYSEX_START = 0xF0
SYSEX_EOX = 0xF7

# Command types
SYSEX_CMD_DEBUG = 0x03      # Debug/logging messages  
SYSEX_CMD_JSON = 0x06       # JSON commands
SYSEX_CMD_JSON_REPLY = 0x07 # JSON responses

# Debug command subcodes
DEBUG_START = 0x01  # Start debug logging
DEBUG_STOP = 0x00   # Stop debug logging

# Complete SysEx commands
SYSEX_DEBUG_START = [SYSEX_START] + DELUGE_MANUFACTURER_ID + [DELUGE_DEVICE_ID, SYSEX_CMD_DEBUG, 0x00, DEBUG_START, SYSEX_EOX]
SYSEX_DEBUG_STOP = [SYSEX_START] + DELUGE_MANUFACTURER_ID + [DELUGE_DEVICE_ID, SYSEX_CMD_DEBUG, 0x00, DEBUG_STOP, SYSEX_EOX]

# Session request for JSON commands
def create_session_request(uuid_tag):
    """Create a session request SysEx message"""
    import json
    prefix = [SYSEX_START] + DELUGE_MANUFACTURER_ID + [DELUGE_DEVICE_ID, SYSEX_CMD_JSON, 0x00]
    msg_obj = {"session": {"tag": uuid_tag}}
    cmd_json = json.dumps(msg_obj)
    cmd_bytes = cmd_json.encode('utf-8')
    return prefix + list(cmd_bytes) + [SYSEX_EOX]

# File operations use the DelugeWeb protocol to read XML files from /SONGS/ directory


