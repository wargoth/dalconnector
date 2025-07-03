from .config import DELUGE_MIDI_PORT_NAME, MIDI_TIMEOUT
from .config import DELUGE_MANUFACTURER_ID, DELUGE_DEVICE_ID, SYSEX_START, SYSEX_EOX
from .config import SYSEX_CMD_JSON, SYSEX_DEBUG_START, create_session_request
from .config import WATCH_FOR_NEW_SAVES, NEW_SAVE_SLEEP_TIMER
from .deluge2ableton import Deluge2Ableton
from .local import propername, displayname

import _thread
import logging
import re
import time
import mido
import json
import uuid

from time import sleep

logger = logging.getLogger(__name__)


class Fetcher(object):
    MAX_RECURSION = 250

    SLEEPTIME = 1.0

    KNOWN_CACHE = {}           # What's the last known song in a series...  2, 2a, 2b, 2c...

    def start(self, ts):
        self.ts = ts
        self.nextsong = None
        self.scanstarttime = None

        # logger.info(f' FETCHER THREAD STARTING')

        try:
            self.loop()
        except Exception as e:
            logger.info(f'MAJOR THREAD EXCEPTION!  {e}')

    def loop(self):
        while True:
            if self.ts.isfinished():
                logger.info(u'THREAD EXIT')
                return

            delugesong = self.ts.targetsong()
            if delugesong is not None:
                self.nextsong = None
                self._mainfetch(delugesong)

            if self.nextsong is not None:
                self._nextsongfetch()

            sleep(self.SLEEPTIME)

    def _mainfetch(self, delugesong):
        # logger.info(f'Expected song fetch: {delugesong}')

        for i in range(0, 5):
            try:
                xml = self.fetch(delugesong)

                if xml is None:
                    continue

                break
            except Exception as e:
                self.ts.setresult(delugesong = delugesong, xml = None, error = True)
                logger.info(f'DAL Connector - wait for song - ERROR! - {e}')
                return

        if not xml:
            self.ts.setresult(delugesong = None, xml = None, error = True)
            return

        self.ts.setresult(delugesong = delugesong, xml = xml, error = False)
        self.nextsong = self._findunusedname(delugesong)

        # logger.info(f'Fetcher complete')


    def _nextsongfetch(self):
        if self.scanstarttime and time.time() - self.scanstarttime > NEW_SAVE_SLEEP_TIMER:
            self.nextsong = None
            self.ts.setwatchmsg('sleep')
            logger.info(f'! Going to sleep !')
            return

        # logger.info(f'Checking for next song: {self.nextsong}')

        try:
            xml = self.fetch(self.nextsong)

            if not xml:
                # logger.info(f'Next song isnt there yet...')
                return

        except Exception as e:
            logger.info(f'DAL Connector - next song - ERROR! - {e}')
            return

        # logger.info(f'NEXT SONG IS THERE!!!')

        self.ts.setnextsongdata(delugesong = self.nextsong, xml = xml, error = False)

        self.nextsong = self._nextsongname(self.nextsong)
        self.ts.setwatchmsg(displayname(self.nextsong))


    # If they load 017 but have 017A and 017B and 017C we need to find the first one which isn't there
    def _findunusedname(self, delugesong):
        self.scanstarttime = time.time()

        self.ts.setwatchmsg('scanning...')

        ######################################################
        # CACHE LOOKUP
        if delugesong in self.KNOWN_CACHE:
            blankname = self.KNOWN_CACHE[delugesong]
        else:
            blankname = delugesong
        ######################################################

        for i in range(0, self.MAX_RECURSION):
            self.KNOWN_CACHE[delugesong] = blankname

            prev = blankname
            blankname = self._nextsongname(blankname)

            # logger.info(f'TRYING: {blankname}')
            xml = self.fetch(blankname)

            if xml is None:
                # logger.info(f'RETRY SOCKET')
                blankname = prev
                continue

            if len(xml) > 0:
                logger.info(f'{len(xml)}')
                continue

            # logger.info(f'FOUND BLANK NAME!  {blankname}')
            self.ts.setwatchmsg(displayname(blankname))
            return blankname

        logger.info(f'ERROR!  MAX RECURSION')
        self.ts.setwatchmsg('error')
        return None


    def fetch(self, delugesong):
        if not delugesong:
            return ''

        # Use DelugeWeb file reading protocol to fetch song XML files from SONGS directory
        try:
            # Find the Deluge MIDI port
            deluge_port = None
            available_ports = mido.get_output_names()
            
            for port_name in available_ports:
                if DELUGE_MIDI_PORT_NAME in port_name:
                    deluge_port = port_name
                    break
            
            if not deluge_port:
                logger.info(f'ERROR: Deluge MIDI port "{DELUGE_MIDI_PORT_NAME}" not found')
                logger.info(f'Available ports: {available_ports}')
                return None

            # Open MIDI connection
            with mido.open_output(deluge_port) as outport, mido.open_input(deluge_port) as inport:
                # First, establish a session with the Deluge
                session_uuid = str(uuid.uuid4())
                session_request = create_session_request(session_uuid)
                
                logger.info(f'Establishing session with Deluge for song {delugesong}...')
                sysex_msg = mido.Message('sysex', data=session_request)
                outport.send(sysex_msg)
                
                # Wait for session response
                session_established = False
                session_data = None
                timeout_time = time.time() + MIDI_TIMEOUT
                
                while time.time() < timeout_time:
                    for msg in inport.iter_pending():
                        if msg.type == 'sysex':
                            session_data = self._handle_session_response(msg.data, session_uuid)
                            if session_data:
                                session_established = True
                                break
                    if session_established:
                        break
                    time.sleep(0.01)
                
                if not session_established:
                    logger.info(f'ERROR: Could not establish session with Deluge')
                    return None
                
                # Get sequence number range from session
                seq_min = session_data.get('seqMin', 1)
                seq_max = session_data.get('seqMax', 254)
                current_seq = seq_min
                
                # Construct song file path (SONG001.XML format)
                song_filename = f"SONG{delugesong.upper().zfill(3)}.XML"
                song_path = f"/SONGS/{song_filename}"
                
                logger.info(f'Requesting song file: {song_path}')
                
                # Open the song file
                file_data = self._read_file_from_deluge(outport, inport, song_path, current_seq, seq_max)
                
                if file_data:
                    # Convert bytes to string (XML)
                    xml_content = file_data.decode('utf-8', errors='ignore')
                    logger.info(f'Successfully read song file {song_filename} ({len(xml_content)} characters)')
                    return xml_content
                else:
                    logger.info(f'Song file {song_filename} not found or could not be read')
                    return None

        except Exception as e:
            logger.info(f'ERROR: MIDI Exception {e}')
            return None
    
    def _handle_session_response(self, data, expected_uuid):
        """Handle session establishment response from Deluge"""
        try:
            # Check if this is a Deluge JSON response
            if (len(data) > 7 and 
                data[1:4] == DELUGE_MANUFACTURER_ID and 
                data[4] == DELUGE_DEVICE_ID and 
                data[5] == 0x07):  # JSON response command (0x07)
                
                # Extract JSON payload
                json_start = 7
                json_end = len(data) - 1  # Remove SYSEX_EOX
                json_bytes = data[json_start:json_end]
                json_str = json_bytes.decode('utf-8')
                
                response = json.loads(json_str)
                if '^session' in response:
                    session_data = response['^session']
                    if session_data.get('tag') == expected_uuid:
                        logger.info(f'Session established successfully')
                        return session_data  # Return the full session data
        except Exception as e:
            logger.info(f'Error parsing session response: {e}')
        
        return None
    
    def _handle_song_response(self, data):
        """Handle song data response from Deluge (when implemented)"""
        try:
            # Check if this is a Deluge JSON response
            if (len(data) > 7 and 
                data[1:4] == DELUGE_MANUFACTURER_ID and 
                data[4] == DELUGE_DEVICE_ID and 
                data[5] == 0x05):  # JSON response command
                
                # Extract JSON payload
                json_start = 7
                json_end = len(data) - 1  # Remove SYSEX_EOX
                json_bytes = data[json_start:json_end]
                json_str = json_bytes.decode('utf-8')
                
                response = json.loads(json_str)
                if 'songData' in response:
                    song_data = response['songData']
                    if 'xml' in song_data:
                        return song_data['xml']
        except Exception as e:
            logger.info(f'Error parsing song response: {e}')
        
        return None
    
    def _read_file_from_deluge(self, outport, inport, file_path, seq_num, seq_max):
        """Read a file from Deluge using DelugeWeb protocol"""
        try:
            # Step 1: Open the file
            open_cmd = {
                "open": {
                    "path": file_path,
                    "write": 0  # 0 = read mode
                }
            }
            
            open_response = self._send_json_command(outport, inport, open_cmd, seq_num)
            if not open_response or open_response.get('err', -1) != 0:
                logger.info(f'Could not open file: {file_path}')
                return None
            
            fid = open_response.get('fid')
            file_size = open_response.get('size', 0)
            
            if not fid or fid < 1:
                logger.info(f'Invalid file descriptor returned: {fid}')
                return None
            
            seq_num = (seq_num + 1) if seq_num < seq_max else 1
            
            # Step 2: Read data in blocks
            file_data = bytearray()
            block_size = 512
            current_addr = 0
            
            logger.info(f'Reading file {file_path} (size: {file_size} bytes)')
            
            while current_addr < file_size:
                read_cmd = {
                    "read": {
                        "fid": fid,
                        "addr": current_addr,
                        "size": min(block_size, file_size - current_addr)
                    }
                }
                
                block_data = self._send_json_command_with_data(outport, inport, read_cmd, seq_num)
                if not block_data:
                    logger.info(f'No data received at offset {current_addr}')
                    break
                
                file_data.extend(block_data)
                current_addr += len(block_data)
                
                # If we got less than requested, we've reached the end
                if len(block_data) < min(block_size, file_size - current_addr + len(block_data)):
                    break
                
                seq_num = (seq_num + 1) if seq_num < seq_max else 1
            
            # Step 3: Close the file
            close_cmd = {
                "close": {
                    "fid": fid
                }
            }
            self._send_json_command(outport, inport, close_cmd, seq_num)
            
            logger.info(f'Successfully read {len(file_data)} bytes from {file_path}')
            return bytes(file_data)
            
        except Exception as e:
            logger.info(f'Error reading file {file_path}: {e}')
            return None
    
    def _send_json_command(self, outport, inport, command, seq_num):
        """Send a JSON command and wait for response"""
        try:
            # Encode JSON command
            cmd_json = json.dumps(command).encode('utf-8')
            
            # Build SysEx message
            sysex_data = ([SYSEX_START] + DELUGE_MANUFACTURER_ID + 
                         [DELUGE_DEVICE_ID, SYSEX_CMD_JSON, seq_num] + 
                         list(cmd_json) + [SYSEX_EOX])
            
            # Send command
            sysex_msg = mido.Message('sysex', data=sysex_data)
            outport.send(sysex_msg)
            
            # Wait for response
            timeout_time = time.time() + MIDI_TIMEOUT
            
            while time.time() < timeout_time:
                for msg in inport.iter_pending():
                    if msg.type == 'sysex':
                        response = self._parse_json_response(msg.data)
                        if response:
                            return self._extract_response_data(response, command)
                time.sleep(0.01)
            
            logger.info(f'Timeout waiting for response to {list(command.keys())[0]} command')
            return None
            
        except Exception as e:
            logger.info(f'Error sending JSON command: {e}')
            return None
    
    def _parse_json_response(self, data):
        """Parse JSON response from SysEx data"""
        try:
            # Check if this is a Deluge JSON response
            if (len(data) > 7 and 
                data[1:4] == DELUGE_MANUFACTURER_ID and 
                data[4] == DELUGE_DEVICE_ID and 
                data[5] == 0x07):  # JSON response command (0x07)
                
                # Extract JSON payload
                json_start = 7
                json_end = len(data) - 1  # Remove SYSEX_EOX
                json_bytes = data[json_start:json_end]
                json_str = json_bytes.decode('utf-8')
                
                return json.loads(json_str)
        except Exception as e:
            logger.info(f'Error parsing JSON response: {e}')
        
        return None
    
    def _extract_response_data(self, response, original_command):
        """Extract relevant data from JSON response based on original command"""
        try:
            cmd_type = list(original_command.keys())[0]
            response_key = f"^{cmd_type}"
            
            if response_key in response:
                resp_data = response[response_key]
                
                if cmd_type == "open":
                    # Return the full response data for open command
                    return resp_data
                
                elif cmd_type == "read":
                    # Return the response data - binary data handled separately
                    return resp_data
                
                elif cmd_type == "close":
                    # Return success status
                    return resp_data.get("err", -1) == 0
        
        except Exception as e:
            logger.info(f'Error extracting response data: {e}')
        
        return None
    
    def _send_json_command_with_data(self, outport, inport, command, seq_num):
        """Send a JSON command and wait for response with binary data extraction"""
        try:
            # Encode JSON command
            cmd_json = json.dumps(command).encode('utf-8')
            
            # Build SysEx message
            sysex_data = ([SYSEX_START] + DELUGE_MANUFACTURER_ID + 
                         [DELUGE_DEVICE_ID, SYSEX_CMD_JSON, seq_num] + 
                         list(cmd_json) + [SYSEX_EOX])
            
            # Send command
            sysex_msg = mido.Message('sysex', data=sysex_data)
            outport.send(sysex_msg)
            
            # Wait for response
            timeout_time = time.time() + MIDI_TIMEOUT
            
            while time.time() < timeout_time:
                for msg in inport.iter_pending():
                    if msg.type == 'sysex':
                        # For read commands, we need to extract binary data from full SysEx
                        cmd_type = list(command.keys())[0]
                        if cmd_type == "read":
                            return self._extract_read_data(msg.data)
                        else:
                            response = self._parse_json_response(msg.data)
                            if response:
                                return self._extract_response_data(response, command)
                time.sleep(0.01)
            
            logger.info(f'Timeout waiting for response to {list(command.keys())[0]} command')
            return None
            
        except Exception as e:
            logger.info(f'Error sending JSON command with data: {e}')
            return None
    
    def _extract_read_data(self, sysex_data):
        """Extract binary data from read command response"""
        try:
            # First parse the JSON response to check for errors
            response = self._parse_json_response(sysex_data)
            if not response or "^read" not in response:
                return None
            
            read_resp = response["^read"]
            if read_resp.get("err") != 0:
                return None
            
            # Find the zero separator between JSON and binary data
            # Start searching after the SysEx header and sequence number
            payload_start = 7  # After [F0 00 21 7B 01 07 seq]
            zero_x = len(sysex_data) - 1  # Default to end if no separator found
            
            # Search for null separator (0x00) that marks end of JSON
            for i in range(payload_start, len(sysex_data) - 1):
                if sysex_data[i] == 0x00:
                    zero_x = i
                    break
            
            # If binary data exists, extract and unpack it
            if zero_x < len(sysex_data) - 2:  # Must have at least separator + 1 byte + F7
                binary_data = self._extract_attached_data(sysex_data, zero_x)
                return bytes(binary_data)
            
            return b""  # No binary data found
            
        except Exception as e:
            logger.info(f'Error extracting read data: {e}')
            return None

    def _unpack_7bit_to_8bit(self, src_data, src_offset, src_len):
        """Unpack 7-bit MIDI data to 8-bit binary data (from DelugeWeb)"""
        try:
            packets = (src_len + 7) // 8  # Ceiling division
            missing = (8 * packets - src_len)
            if missing == 7:  # This would be weird
                packets -= 1
                missing = 0
            
            out_len = 7 * packets - missing
            if out_len <= 0:
                return bytearray()
            
            dst = bytearray(out_len)
            
            for i in range(packets):
                ipos = 8 * i
                opos = 7 * i
                
                # Fill output section with zeros
                for j in range(7):
                    if opos + j >= out_len:
                        break
                    dst[opos + j] = 0
                
                # Unpack data
                for j in range(7):
                    if j + 1 + ipos >= src_len:
                        break
                    if opos + j >= out_len:
                        break
                    
                    dst[opos + j] = src_data[src_offset + ipos + 1 + j] & 0x7f
                    if src_data[src_offset + ipos] & (1 << j):
                        dst[opos + j] |= 0x80
            
            return dst
        except Exception as e:
            logger.info(f'Error unpacking 7-bit data: {e}')
            return bytearray()
    
    def _extract_attached_data(self, data, zero_x_pos):
        """Extract attached binary data from SysEx message"""
        try:
            tot_len = len(data)
            att_len = tot_len - zero_x_pos - 2  # Ignore 0 separator & ending 0xF7
            
            if att_len <= 0:
                return bytearray()
            
            # Calculate expected output size
            packets = (att_len + 7) // 8
            missing = (8 * packets - att_len)
            if missing == 7:
                packets -= 1
                missing = 0
            out_len = 7 * packets - missing
            
            # Unpack the data
            return self._unpack_7bit_to_8bit(data, zero_x_pos + 1, att_len)
            
        except Exception as e:
            logger.info(f'Error extracting attached data: {e}')
            return bytearray()

    def _nextsongname(self, name):
        def nextletter(letter):
           return chr((ord(letter) - 64) % 26 + 65)

        if not name:
            return None

        name = propername(name)

        if name.isdecimal():
            return f"{name}A"

        if name.endswith('Z'):
            return propername(f"{str(int(name[0:-1]) + 1)}")

        return f"{name[0:-1]}{nextletter(name[-1])}"




class ThreadShare(object):
    def __init__(self):
        self.watchmsg = None
        self.finished = False
        self.reset()

        try:
            self.fetcher = Fetcher()
            _thread.start_new_thread(self.fetcher.start, (self, ) )
        except Exception as e:
            logger.info(f'Error: unable to start thread {e}')

    def reset(self):
        self.delugesong = None
        self.currentsongdata = None
        self.nextsongdata = None


    ############################################
    # CURRENT SONG
    def targetsong(self):
        return self.delugesong

    def fetchsong(self, delugesong):
        self.currentsongdata = None

        self.delugesong = delugesong

    def setresult(self, delugesong, xml, error):
        self.delugesong = None

        if not xml:
            self.currentsongdata = { 'songhsh': None, 'error': True }
        else:
            songhsh = Deluge2Ableton.convert(xml)
            self.currentsongdata = { 'songhsh': songhsh, 'error': error }

    def getresult(self, delugesong):
        # delugesong should never be None
        if delugesong is None:
            return { 'xml': None, 'error': True }

        if self.currentsongdata is None:
            return None

        value = self.currentsongdata
        self.currentsongdata = None

        return value


    ############################################
    # NEXT SONG
    def getnextsongdata(self):
        if not self.nextsongdata:
            return None

        value = self.nextsongdata
        self.nextsongdata = None
        return value

    def setnextsongdata(self, delugesong, xml, error):
        songhsh = Deluge2Ableton.convert(xml)

        self.nextsongdata = { 'songhsh': songhsh, 'error': error, 'delugesong': delugesong }

    ############################################
    # SCANNING
    def setwatchmsg(self, msg):
        self.watchmsg = msg

    def getwatchmsg(self):
        if self.watchmsg is None:
            return self.watchmsg

        value = self.watchmsg
        self.watchmsg = None
        return value

    ############################################

    def isfinished(self):
        return self.finished

    def disconnect(self):
        self.reset()
        # logger.info(u'Tracker knows we are done....')
        self.finished = True


