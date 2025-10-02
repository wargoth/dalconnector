# DALConnector USB Debug Guide

## Step 1: Check if DALConnector is Loading

1. **Open Ableton Live**
2. **Check Control Surface Settings**:
   - Go to Preferences > Link/Tempo/MIDI
   - In Control Surface dropdown, verify DALConnector is selected
   - Input should be set to "Deluge" or similar
   - Output should be set to "Deluge" or similar

3. **Check Ableton Log**:
   - Help > Open Log File (or manually open log file)
   - Look for these messages when Ableton starts:
   ```
   --- DAL Connector Started ---
   Connection method: USB
   Watch for new saves: True
   ```

**If you don't see these messages**: DALConnector is not loading properly.

## Step 2: Test Track Name Detection

1. **Create a MIDI track**
2. **Rename it to "dc:1"** (exactly - no spaces)
3. **Select the track**

**Expected log messages**:
```
Track name changed: "dc:1"
Valid dc: track detected: "dc:1"
Handling track change for: "dc:1"
Parsed Deluge song: SONG001.XML
Creating USB thread share...
Initializing USBThreadShare...
Creating USBFetcher...
Starting USB fetcher thread...
USB thread started successfully
```

**If you don't see these messages**: Track name detection is not working.

## Step 3: Check USB Thread Startup

**Expected log messages after track selection**:
```
USBFetcher.start() called
Using Ableton's native MIDI framework for USB communication
Testing connection to Deluge...
Sending ping to Deluge: ['0xf0', '0x0', '0x21', '0x7b', '0x1', '0x0', '0xf7']
Sending SysEx via Ableton: ['0xf0', '0x0', '0x21', '0x7b', '0x1', '0x0', '0xf7']
SysEx sent successfully
Ping sent, waiting for pong response...
```

## Step 4: Check for Pong Response

**If Deluge is connected and responding**:
```
Received MIDI: ['0xf0', '0x0', '0x21', '0x7b', '0x1', '0x7f', '0xf7']
Deluge SysEx command: 7F
Handling pong response
Pong received - connection successful!
USB FETCHER THREAD STARTING - connection successful
```

**If no pong response**:
```
Ping timeout - no pong response received
Failed to establish connection to Deluge
```

## Common Issues and Solutions

### Issue 1: No DALConnector startup logs
**Problem**: DALConnector script not loading
**Solutions**:
- Check script is in correct folder: `MIDI Remote Scripts/DALConnector/`
- Verify all files are present: `DALConnector.py`, `usb_fetcher.py`, etc.
- Check for Python syntax errors in log file
- Restart Ableton Live

### Issue 2: No track name detection logs
**Problem**: Track name listener not working
**Solutions**:
- Use exact format: "dc:1" (no extra spaces)
- Try "dc:1a" for song SONG001A.XML
- Check if other control surfaces are interfering
- Restart Ableton Live

### Issue 3: SysEx send fails
**Problem**: `Error sending SysEx` in logs
**Solutions**:
- Check MIDI port assignment in Ableton preferences
- Verify Deluge is set as both Input and Output for DALConnector
- Try different USB cable/port
- Check Deluge is in USB MIDI mode

### Issue 4: No MIDI received
**Problem**: No incoming MIDI messages in logs
**Solutions**:
- Check Deluge is powered on and connected
- Verify USB cable supports data (not charge-only)
- Check Deluge MIDI settings (should be default)
- Try sending MIDI from Deluge manually to test

### Issue 5: Wrong MIDI device
**Problem**: Receiving MIDI but not from Deluge
**Solutions**:
- Check Deluge manufacturer ID in received messages
- Should see: `['0xf0', '0x0', '0x21', '0x7b', '0x1', ...]`
- If different ID, wrong device is assigned

## Advanced Debugging

### Enable Verbose Logging
Add this to `DALConnector.py` `__init__` method:
```python
logging.getLogger().setLevel(logging.DEBUG)
```

### Test MIDI Manually
Try these in Ableton's MIDI monitor or external tool:
- Send ping: `F0 00 21 7B 01 00 F7`
- Should receive pong: `F0 00 21 7B 01 7F F7`

### Check Deluge Firmware
- Ensure Deluge firmware supports SysEx (version 4.0+)
- Check Deluge MIDI settings are default
- Try factory reset MIDI settings if needed

## Log File Locations

**Windows**: `%USERPROFILE%\AppData\Roaming\Ableton\Live 11 Suite\Preferences\Log.txt`
**macOS**: `~/Library/Preferences/Ableton/Live 11 Suite/Log.txt`

## Next Steps

1. Follow this guide step by step
2. Copy the exact log messages you see (or don't see)
3. Note which step fails
4. Check the corresponding solution section