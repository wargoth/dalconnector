<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/baronrabban/dalconnector">
    <img src="images/logo.png" alt="Logo" width="843" height="235">
  </a>

  <h3 align="center">DAL Connector - Deluge Ableton Live Connector</h3>

  <p align="center">
    A control surface script for connecting a Synthstrom Deluge to Ableton Live 11 via USB MIDI
    <br />
    <br />
    <a href="https://youtu.be/ZGC71gpfkwQ&vq=hd1080"><strong>View Demo</strong></a>
    <br />
    <br />
    <a href="https://github.com/baronrabban/dalconnector/issues">Report Bug</a>
    ·
    <a href="https://github.com/baronrabban/dalconnector/issues">Request Feature</a>
  </p>
</p>





<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#requirements">Requirements</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#Troubleshooting">Troubleshooting</a></li>
    <li><a href="#FAQ">FAQ</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
    <li><a href="#about-this-usb-midi-version">About This USB MIDI Version</a></li>
  </ol>
</details>




<!-- GETTING STARTED -->
## Getting Started

Download the latest version of the reposority

### Requirements

* A Deluge
* Ableton Live 11 - Earlier versions not supported, see FAQ
* USB connection between Deluge and computer
* Python MIDI libraries (mido, python-rtmidi) - see installation section


### Installation

1. Connect your Deluge to your computer via USB cable

2. Download the latest release from [Releases](https://github.com/baronrabban/dalconnector/releases)

3. Install required Python dependencies:
   ```bash
   pip3 install mido python-rtmidi
   ```
   
   Or use the requirements file:
   ```bash
   pip3 install -r requirements.txt
   ```

4. Test your setup:
   ```bash
   python3 test_midi_connection.py
   python3 test_song_fetch.py 001
   ```

5. Put the DALConnector folder in your Ableton "MIDI Remote Scripts" directory. Ableton provides guidance: [How to install a control surface script](https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts)

6. In Ableton, under Options -> Preferences -> Link/Tempo/Midi add a new control surface. If DALConnector isn't in the list, something went wrong.

7. Edit the title of a MIDI track with a song you have saved on your Deluge, such as "dc:4a" if you want song 4a


<!-- Troubleshooting -->
### Troubleshooting

**Log.txt file**:
Live has a log.txt file which DAL Connector writes to. Near the bottom of the page [Finding the log.txt file](https://help.ableton.com/hc/en-us/articles/209071629-Where-to-find-Crash-Reports) is a description of where to find the log.txt file

**USB Connection**:
- Ensure your Deluge is connected via USB and recognized by your system
- Check that the Deluge appears in your MIDI device list (usually as "Deluge Port 3")
- Make sure the required Python MIDI libraries are installed (mido, python-rtmidi)

**MIDI Port Issues**:
- If the Deluge MIDI port is not found, check the config.py file and verify the DELUGE_MIDI_PORT_NAME setting
- Try different USB ports or cables if connection is unstable

**Song File Issues**:
- Test song fetching with: `python3 test_song_fetch.py 001`
- Make sure you have songs saved on your Deluge in the SONGS directory
- Song files must be saved in XML format (standard Deluge format)
- Check that the song number matches the file on your Deluge (e.g., "dc:4a" looks for SONG004.XML)


<!-- FAQ -->
## FAQ

**Q:** Why does it only work with Ableton 11?

 **A:** Ableton switched some backend code on 11 and I wrote it with that in mind.  It's likely the code could be backported to earlier versions if someone wants to try that.
##

**Q:** Do I need a WiFi SD card anymore?

 **A:** No! This version has been updated to use USB MIDI communication instead of WiFi SD cards. Simply connect your Deluge via USB.
##

**Q:** What happened to the FlashAir card requirement?

 **A:** The original version required a Toshiba FlashAir WiFi SD card, but this has been rewritten to use USB MIDI communication, making it more reliable and easier to set up.
##

**Q:** Can this work with the original FlashAir method?

 **A:** This version only supports USB MIDI. If you need FlashAir support, you'll need to use the original version of DALConnector.
##

**Q:** How does it get song data from the Deluge?

 **A:** It uses the DelugeWeb SysEx protocol to read XML files directly from the Deluge's `/SONGS/` directory via USB MIDI. No special firmware is needed - it works with current Deluge firmware.
##



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

Distributed under the The 2-Clause BSD License. See `LICENSE` for more information.




<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
* [Downrush](https://github.com/jamiefaye/downrush)  Credit to Downrush and Jamie Fenton for my understanding of notedata and decoding bpm
* [DelugeWeb](https://github.com/jamiefaye/DelugeWeb) The actual Deluge SysEx protocol implementation that made this USB version possible
* [Delugian](https://github.com/alifeinbinary/Delugian) Inspiration for the USB MIDI approach and companion app concept


## About This USB MIDI Version

This version of DALConnector has been rewritten to use USB MIDI communication instead of WiFi SD cards, inspired by the approach used in the [Delugian](https://github.com/alifeinbinary/Delugian) project.

### Key Changes from Original:
- **USB MIDI**: Direct communication via USB instead of WiFi SD card
- **Simplified Setup**: No need for FlashAire cards or WiFi configuration  
- **More Reliable**: USB connection is more stable than WiFi
- **Python MIDI**: Uses `mido` and `python-rtmidi` libraries for MIDI communication

### Relationship to Other Projects:
- **Delugian** is a full-featured cross-platform companion app (Tauri/React/TypeScript)
- **DALConnector** is specifically an Ableton Live control surface script (Python)
- **DelugeWeb** provided the actual SysEx protocol implementation that this version uses
- All projects use USB MIDI to communicate with the Deluge
- DALConnector focuses specifically on song import/sync with Ableton

**Note**: This version now uses the **actual working SysEx protocol** from the DelugeWeb project to read song XML files directly from the Deluge's `/SONGS/` directory via USB MIDI. The file reading functionality is implemented and should work with current Deluge firmware.

### Current Status:
- **✅ Real SysEx protocol implemented**: Based on DelugeWeb project findings
- **✅ Session management**: Proper handshake with Deluge device
- **✅ JSON command structure**: Framework for sending/receiving JSON commands
- **✅ File reading capability**: Can read XML files from Deluge's SONGS directory
- **🔄 Binary data handling**: 7-bit to 8-bit unpacking for file data

### Protocol Details:
- **Manufacturer ID**: `0x00, 0x21, 0x7B` (Synthstrom Audible)
- **Device ID**: `0x01` (Deluge)
- **Command Types**: Debug logging (0x03), JSON commands (0x04), JSON responses (0x05)
- **Session-based**: Establishes connection session before sending commands
- **File Operations**: Uses `open`, `read`, `close` commands to access song XML files

### Current Status:
- **🔄 Testing needed**: File reading implementation needs testing with actual Deluge hardware
- **🔄 Binary data handling**: 7-bit to 8-bit unpacking may need refinement
- **⚠️ File path format**: Song file naming convention may need adjustment (SONG001.XML vs other formats)

### How It Works:
1. **Session Establishment**: Creates UUID-based session with Deluge
2. **File Access**: Opens song files from `/SONGS/SONG###.XML` path
3. **Block Reading**: Reads file data in 512-byte blocks
4. **Data Conversion**: Unpacks 7-bit MIDI data to 8-bit file content
5. **XML Processing**: Converts file bytes to XML string for Ableton processing

### Future Development:
This implementation uses the **actual working DelugeWeb protocol** and should work with current Deluge firmware once testing and any needed refinements are complete.


