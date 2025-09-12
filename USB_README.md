# DALConnector USB Implementation

This implementation adds USB connectivity to DALConnector, allowing direct communication with the Synthstrom Deluge over USB using the MIDI SysEx protocol.

## Features

- **Direct USB Connection**: No need for WiFi SD cards or network setup
- **SysEx Protocol**: Uses Deluge's native MIDI SysEx protocol for file operations
- **Backward Compatibility**: WiFi connection still supported as legacy option
- **Automatic Detection**: Automatically finds and connects to Deluge MIDI ports

## Requirements

- Python 3.6+
- `python-rtmidi>=1.4.0`
- Synthstrom Deluge connected via USB
- Deluge firmware that supports SysEx file operations

## Installation

1. Install the MIDI library:
   ```bash
   pip install python-rtmidi
   ```

2. Configure connection method in `config.py`:
   ```python
   CONNECTION_METHOD = "USB"  # Default setting
   ```

3. Connect your Deluge via USB and ensure it's recognized as a MIDI device

## Testing

Run the test script to verify your USB connection:

```bash
python test_usb_connection.py
```

This will:
- Find available MIDI ports
- Connect to the Deluge
- Test ping/pong communication
- Test JSON file operations

## Troubleshooting

### "Deluge MIDI ports not found"
- Ensure Deluge is connected via USB
- Check that Deluge appears in your system's MIDI devices
- Try unplugging and reconnecting the USB cable
- On some systems, you may need to restart the Deluge

### "python-rtmidi not installed"
```bash
pip install python-rtmidi
```

### Connection timeout or no response
- Make sure the Deluge is not in a menu or engaged in SD card operations
- Try the test script first to verify basic connectivity
- Check Ableton's log files for detailed error messages

## Implementation Details

### Protocol
- Uses Deluge SysEx specification (see `deluge-sysex-spec.md`)
- Commands: Ping/Pong, JSON file operations
- 7-bit to 8-bit data packing/unpacking
- Request/response sequence numbering

### Files
- `usb_fetcher.py`: Main USB SysEx implementation
- `config.py`: Connection method configuration  
- `test_usb_connection.py`: Test script
- `requirements.txt`: Python dependencies

### Error Handling
- Automatic retry on failed operations
- Graceful fallback on connection issues
- Detailed logging for troubleshooting

## Advantages over WiFi

1. **Reliability**: Direct USB connection eliminates network issues
2. **Speed**: Faster than HTTP over WiFi
3. **Simplicity**: No WiFi card setup required
4. **Security**: No network exposure
5. **Real-time**: Better responsiveness for live use

## Migration from WiFi

To switch from WiFi to USB:
1. Install `python-rtmidi`
2. Set `CONNECTION_METHOD = "USB"` in `config.py`
3. Connect Deluge via USB
4. Restart Ableton Live

The WiFi configuration remains available if you need to switch back.