from .config import WATCH_FOR_NEW_SAVES, NEW_SAVE_SLEEP_TIMER
from .deluge2ableton import Deluge2Ableton
from .local import propername, displayname

import _thread
import time
import logging
import json
import threading
from time import sleep

try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False

logger = logging.getLogger(__name__)

class USBFetcher(object):
    """USB SysEx-based fetcher for Deluge communication"""
    
    MAX_RECURSION = 250
    SLEEPTIME = 1.0
    SYSEX_TIMEOUT = 5.0
    
    # Deluge SysEx constants
    DELUGE_SYSEX_HEADER = [0xF0, 0x00, 0x21, 0x7B, 0x01]
    SYSEX_END = 0xF7
    
    # Commands
    CMD_PING = 0x00
    CMD_POPUP = 0x01
    CMD_HID = 0x02
    CMD_DEBUG = 0x03
    CMD_JSON = 0x04
    CMD_JSON_REPLY = 0x05
    CMD_PONG = 0x7F
    
    KNOWN_CACHE = {}
    
    def __init__(self):
        self.midi_out = None
        self.midi_in = None
        self.sequence_num = 1
        self.pending_requests = {}
        self.response_lock = threading.Lock()
        
    def start(self, ts):
        self.ts = ts
        self.nextsong = None
        self.scanstarttime = None
        
        if not RTMIDI_AVAILABLE:
            logger.error("rtmidi not available - cannot use USB connection")
            self.ts.setresult(delugesong=None, xml=None, error=True)
            return
            
        if not self._initialize_midi():
            logger.error("Failed to initialize MIDI connection to Deluge")
            self.ts.setresult(delugesong=None, xml=None, error=True)
            return
            
        logger.info('USB FETCHER THREAD STARTING')
        
        try:
            self.loop()
        except Exception as e:
            logger.error(f'MAJOR USB THREAD EXCEPTION! {e}')
        finally:
            self._cleanup_midi()
            
    def _initialize_midi(self):
        """Initialize MIDI connection to Deluge"""
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_in = rtmidi.MidiIn()
            
            # Find Deluge MIDI ports
            out_ports = self.midi_out.get_ports()
            in_ports = self.midi_in.get_ports()
            
            deluge_out_port = None
            deluge_in_port = None
            
            for i, port_name in enumerate(out_ports):
                if 'Deluge' in port_name or 'deluge' in port_name.lower():
                    deluge_out_port = i
                    break
                    
            for i, port_name in enumerate(in_ports):
                if 'Deluge' in port_name or 'deluge' in port_name.lower():
                    deluge_in_port = i
                    break
                    
            if deluge_out_port is None or deluge_in_port is None:
                logger.error("Deluge MIDI ports not found")
                return False
                
            self.midi_out.open_port(deluge_out_port)
            self.midi_in.open_port(deluge_in_port)
            
            # Set up message callback
            self.midi_in.set_callback(self._midi_callback)
            self.midi_in.ignore_types(False, False, False)  # Don't ignore SysEx
            
            # Test connection with ping
            if not self._ping_deluge():
                logger.error("Deluge not responding to ping")
                return False
                
            logger.info("Successfully connected to Deluge via USB")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MIDI: {e}")
            return False
            
    def _cleanup_midi(self):
        """Clean up MIDI connections"""
        if self.midi_in:
            self.midi_in.close_port()
            self.midi_in = None
        if self.midi_out:
            self.midi_out.close_port()
            self.midi_out = None
            
    def _midi_callback(self, event, data):
        """Handle incoming MIDI messages"""
        message, deltatime = event
        
        # Check if it's a Deluge SysEx message
        if (len(message) >= 7 and 
            message[0] == 0xF0 and 
            message[1:5] == self.DELUGE_SYSEX_HEADER[1:5]):
            
            command = message[5]
            
            if command == self.CMD_JSON_REPLY:
                self._handle_json_reply(message)
            elif command == self.CMD_PONG:
                self._handle_pong(message)
                
    def _handle_json_reply(self, message):
        """Handle JSON reply from Deluge"""
        try:
            if len(message) < 8:
                return
                
            sequence = message[6]
            
            # Find separator or end of message
            json_start = 7
            json_end = len(message) - 1  # Remove 0xF7
            binary_data = None
            
            # Check for binary data separator (0x00)
            for i in range(json_start, json_end):
                if message[i] == 0x00:
                    json_end = i
                    binary_data = message[i+1:-1]  # Data after separator, before 0xF7
                    break
                    
            # Extract JSON
            json_bytes = message[json_start:json_end]
            json_str = ''.join(chr(b) for b in json_bytes)
            
            # Parse JSON response
            response_data = json.loads(json_str)
            
            # Store response for waiting thread
            with self.response_lock:
                self.pending_requests[sequence] = {
                    'json': response_data,
                    'binary': binary_data,
                    'received': True
                }
                
        except Exception as e:
            logger.error(f"Error handling JSON reply: {e}")
            
    def _handle_pong(self, message):
        """Handle pong response"""
        with self.response_lock:
            self.pending_requests['pong'] = {'received': True}
            
    def _ping_deluge(self):
        """Send ping to Deluge and wait for pong"""
        try:
            ping_message = self.DELUGE_SYSEX_HEADER + [self.CMD_PING, self.SYSEX_END]
            
            with self.response_lock:
                self.pending_requests['pong'] = {'received': False}
                
            self.midi_out.send_message(ping_message)
            
            # Wait for pong response
            timeout = time.time() + self.SYSEX_TIMEOUT
            while time.time() < timeout:
                with self.response_lock:
                    if self.pending_requests.get('pong', {}).get('received', False):
                        return True
                sleep(0.1)
                
            return False
            
        except Exception as e:
            logger.error(f"Error sending ping: {e}")
            return False
            
    def _send_json_command(self, command_dict):
        """Send JSON command to Deluge and return sequence number"""
        try:
            sequence = self.sequence_num
            self.sequence_num = (self.sequence_num % 127) + 1
            
            json_str = json.dumps(command_dict)
            json_bytes = [ord(c) & 0x7F for c in json_str]  # Ensure 7-bit clean
            
            message = (self.DELUGE_SYSEX_HEADER + 
                      [self.CMD_JSON, sequence] + 
                      json_bytes + 
                      [self.SYSEX_END])
                      
            with self.response_lock:
                self.pending_requests[sequence] = {'received': False}
                
            self.midi_out.send_message(message)
            return sequence
            
        except Exception as e:
            logger.error(f"Error sending JSON command: {e}")
            return None
            
    def _wait_for_response(self, sequence):
        """Wait for response to a JSON command"""
        timeout = time.time() + self.SYSEX_TIMEOUT
        
        while time.time() < timeout:
            with self.response_lock:
                response = self.pending_requests.get(sequence)
                if response and response.get('received', False):
                    del self.pending_requests[sequence]
                    return response
                    
            sleep(0.1)
            
        # Timeout - clean up
        with self.response_lock:
            if sequence in self.pending_requests:
                del self.pending_requests[sequence]
                
        return None
        
    def loop(self):
        """Main fetcher loop"""
        while True:
            if self.ts.isfinished():
                logger.info('USB THREAD EXIT')
                return
                
            delugesong = self.ts.targetsong()
            if delugesong is not None:
                self.nextsong = None
                self._mainfetch(delugesong)
                
            if self.nextsong is not None:
                self._nextsongfetch()
                
            sleep(self.SLEEPTIME)
            
    def _mainfetch(self, delugesong):
        """Fetch main song from Deluge"""
        for i in range(0, 5):
            try:
                xml = self.fetch(delugesong)
                
                if xml is None:
                    continue
                    
                break
            except Exception as e:
                self.ts.setresult(delugesong=delugesong, xml=None, error=True)
                logger.error(f'DAL Connector USB - wait for song - ERROR! - {e}')
                return
                
        if not xml:
            self.ts.setresult(delugesong=None, xml=None, error=True)
            return
            
        self.ts.setresult(delugesong=delugesong, xml=xml, error=False)
        self.nextsong = self._findunusedname(delugesong)
        
    def _nextsongfetch(self):
        """Fetch next song version if watching for new saves"""
        if self.scanstarttime and time.time() - self.scanstarttime > NEW_SAVE_SLEEP_TIMER:
            self.nextsong = None
            self.ts.setwatchmsg('sleep')
            logger.info('USB fetcher going to sleep')
            return
            
        try:
            xml = self.fetch(self.nextsong)
            
            if not xml:
                return
                
        except Exception as e:
            logger.error(f'DAL Connector USB - next song - ERROR! - {e}')
            return
            
        self.ts.setnextsongdata(delugesong=self.nextsong, xml=xml, error=False)
        self.nextsong = self._nextsongname(self.nextsong)
        self.ts.setwatchmsg(displayname(self.nextsong))
        
    def _findunusedname(self, delugesong):
        """Find the next unused song name in the sequence"""
        self.scanstarttime = time.time()
        self.ts.setwatchmsg('scanning...')
        
        # Cache lookup
        if delugesong in self.KNOWN_CACHE:
            blankname = self.KNOWN_CACHE[delugesong]
        else:
            blankname = delugesong
            
        for i in range(0, self.MAX_RECURSION):
            self.KNOWN_CACHE[delugesong] = blankname
            
            prev = blankname
            blankname = self._nextsongname(blankname)
            
            xml = self.fetch(blankname)
            
            if xml is None:
                blankname = prev
                continue
                
            if len(xml) > 0:
                continue
                
            self.ts.setwatchmsg(displayname(blankname))
            return blankname
            
        logger.error('ERROR! MAX RECURSION in USB fetcher')
        self.ts.setwatchmsg('error')
        return None
        
    def fetch(self, delugesong):
        """Fetch song XML from Deluge via SysEx"""
        if not delugesong:
            return ''
            
        song_path = f"/SONGS/SONG{delugesong}.XML"
        
        try:
            # Open file
            open_cmd = {"open": {"path": song_path, "write": 0}}
            sequence = self._send_json_command(open_cmd)
            
            if sequence is None:
                return None
                
            response = self._wait_for_response(sequence)
            
            if not response:
                logger.error("Timeout waiting for file open response")
                return None
                
            open_result = response['json']
            
            # Check for errors
            if '^open' not in open_result:
                return None
                
            open_data = open_result['^open']
            if open_data.get('err', 0) != 0:
                # File not found or error
                return ""
                
            file_id = open_data.get('fid')
            file_size = open_data.get('size', 0)
            
            if file_id is None or file_size == 0:
                return ""
                
            # Read entire file
            read_cmd = {"read": {"fid": file_id, "offset": 0, "length": file_size}}
            sequence = self._send_json_command(read_cmd)
            
            if sequence is None:
                return None
                
            response = self._wait_for_response(sequence)
            
            if not response:
                logger.error("Timeout waiting for file read response")
                return None
                
            # Check for binary data
            if response['binary'] is None:
                return ""
                
            # Unpack 7-bit to 8-bit data
            xml_data = self._unpack_7bit_to_8bit(response['binary'])
            return xml_data.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.error(f'ERROR: USB fetch exception {e}')
            return None
            
    def _unpack_7bit_to_8bit(self, data):
        """Unpack 7-bit MIDI data to 8-bit bytes using Deluge firmware algorithm"""
        if not data:
            return b''
            
        src_len = len(data)
        packets = (src_len + 7) // 8
        missing = (8 * packets - src_len)
        
        if missing == 7:  # this would be weird
            packets -= 1
            missing = 0
            
        out_len = 7 * packets - missing
        result = bytearray(out_len)
        
        for i in range(packets):
            ipos = 8 * i
            opos = 7 * i
            
            if ipos >= src_len:
                break
                
            rot_bit = 1
            high_bits = data[ipos]
            
            for j in range(7):
                if not (j + 1 + ipos < src_len):
                    break
                if opos + j >= out_len:
                    break
                    
                result[opos + j] = data[ipos + 1 + j] & 0x7F
                if high_bits & rot_bit:
                    result[opos + j] |= 0x80
                rot_bit <<= 1
                
        return bytes(result)
        
    def _nextsongname(self, name):
        """Generate next song name in sequence (same logic as original fetcher)"""
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


class USBThreadShare(object):
    """Thread-safe communication interface for USB fetcher"""
    
    def __init__(self):
        self.watchmsg = None
        self.finished = False
        self.reset()
        
        try:
            self.fetcher = USBFetcher()
            _thread.start_new_thread(self.fetcher.start, (self,))
        except Exception as e:
            logger.error(f'Error: unable to start USB thread {e}')
            
    def reset(self):
        self.delugesong = None
        self.currentsongdata = None
        self.nextsongdata = None
        
    # CURRENT SONG
    def targetsong(self):
        return self.delugesong
        
    def fetchsong(self, delugesong):
        self.currentsongdata = None
        self.delugesong = delugesong
        
    def setresult(self, delugesong, xml, error):
        self.delugesong = None
        
        if not xml:
            self.currentsongdata = {'songhsh': None, 'error': True}
        else:
            songhsh = Deluge2Ableton.convert(xml)
            self.currentsongdata = {'songhsh': songhsh, 'error': error}
            
    def getresult(self, delugesong):
        if delugesong is None:
            return {'xml': None, 'error': True}
            
        if self.currentsongdata is None:
            return None
            
        value = self.currentsongdata
        self.currentsongdata = None
        
        return value
        
    # NEXT SONG
    def getnextsongdata(self):
        if not self.nextsongdata:
            return None
            
        value = self.nextsongdata
        self.nextsongdata = None
        return value
        
    def setnextsongdata(self, delugesong, xml, error):
        songhsh = Deluge2Ableton.convert(xml)
        self.nextsongdata = {'songhsh': songhsh, 'error': error, 'delugesong': delugesong}
        
    # SCANNING
    def setwatchmsg(self, msg):
        self.watchmsg = msg
        
    def getwatchmsg(self):
        if self.watchmsg is None:
            return self.watchmsg
            
        value = self.watchmsg
        self.watchmsg = None
        return value
        
    def isfinished(self):
        return self.finished
        
    def disconnect(self):
        self.reset()
        self.finished = True