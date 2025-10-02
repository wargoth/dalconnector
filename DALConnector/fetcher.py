from .config import WATCH_FOR_NEW_SAVES, NEW_SAVE_SLEEP_TIMER
from .deluge2ableton import Deluge2Ableton
from .local import propername, displayname

import logging
import time
import json
import _thread
from time import sleep

logger = logging.getLogger(__name__)


class Fetcher(object):
    """USB SysEx-based fetcher for Deluge communication using Ableton's native MIDI"""

    MAX_RECURSION = 250
    SLEEPTIME = 1.0
    SYSEX_TIMEOUT = 5.0

    # Deluge SysEx constants
    DELUGE_SYSEX_HEADER = [0xF0, 0x00, 0x21, 0x7B, 0x01]
    SYSEX_END = 0xF7

    # Commands
    CMD_PING = 0x00
    CMD_JSON = 0x04
    CMD_JSON_REPLY = 0x05
    CMD_PONG = 0x7F

    KNOWN_CACHE = {}

    def __init__(self, control_surface):
        """Initialize fetcher with reference to control surface for MIDI communication"""
        self.control_surface = control_surface
        self.sequence_num = 1
        self.pending_responses = {}
        self.response_callbacks = {}

    def start(self, ts):
        self.ts = ts
        self.nextsong = None
        self.scanstarttime = None

        logger.info('USB Fetcher starting (using Ableton native SysEx)')

        try:
            self.loop()
        except Exception as e:
            logger.error(f'MAJOR THREAD EXCEPTION! {e}')

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


    def handle_sysex_response(self, sysex_data):
        """Called by control surface when SysEx response is received"""
        try:
            if len(sysex_data) < 8:
                return

            # Verify Deluge SysEx
            if list(sysex_data[0:5]) != self.DELUGE_SYSEX_HEADER:
                return

            command = sysex_data[5]

            if command == self.CMD_JSON_REPLY:
                sequence = sysex_data[6]

                # Parse JSON and binary data
                json_start = 7
                json_end = len(sysex_data) - 1
                binary_data = None

                for i in range(json_start, json_end):
                    if sysex_data[i] == 0x00:
                        json_end = i
                        binary_data = sysex_data[i+1:-1]
                        break

                json_bytes = sysex_data[json_start:json_end]
                json_str = ''.join(chr(b) for b in json_bytes)
                response_data = json.loads(json_str)

                # Store response
                self.pending_responses[sequence] = {
                    'json': response_data,
                    'binary': binary_data,
                    'received': True
                }

                # Call callback if registered
                if sequence in self.response_callbacks:
                    callback = self.response_callbacks[sequence]
                    del self.response_callbacks[sequence]
                    callback(response_data, binary_data)

        except Exception as e:
            logger.error(f"Error handling SysEx response: {e}")

    def _send_json_command(self, command_dict, callback=None):
        """Send JSON command to Deluge via SysEx"""
        try:
            sequence = self.sequence_num
            self.sequence_num = (self.sequence_num % 127) + 1

            json_str = json.dumps(command_dict)
            json_bytes = [ord(c) & 0x7F for c in json_str]

            message = tuple(self.DELUGE_SYSEX_HEADER +
                          [self.CMD_JSON, sequence] +
                          json_bytes +
                          [self.SYSEX_END])

            self.pending_responses[sequence] = {'received': False}
            if callback:
                self.response_callbacks[sequence] = callback

            # Send via control surface
            self.control_surface._send_midi(message)
            logger.debug(f"Sent JSON command sequence {sequence}: {command_dict}")

            return sequence

        except Exception as e:
            logger.error(f"Error sending JSON command: {e}")
            return None

    def _wait_for_response(self, sequence, timeout=None):
        """Wait for response to a JSON command"""
        if timeout is None:
            timeout = self.SYSEX_TIMEOUT

        deadline = time.time() + timeout

        while time.time() < deadline:
            response = self.pending_responses.get(sequence)
            if response and response.get('received', False):
                del self.pending_responses[sequence]
                return response
            sleep(0.1)

        # Timeout
        if sequence in self.pending_responses:
            del self.pending_responses[sequence]
        return None

    def _unpack_7bit_to_8bit(self, data):
        """Unpack 7-bit MIDI data to 8-bit bytes"""
        if not data:
            return b''

        src_len = len(data)
        packets = (src_len + 7) // 8
        missing = (8 * packets - src_len)

        if missing == 7:
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

    def fetch(self, delugesong):
        """Fetch song XML from Deluge via USB SysEx"""
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
                logger.debug(f"Timeout waiting for file open: {song_path}")
                return ""

            open_result = response['json']

            if '^open' not in open_result:
                return ""

            open_data = open_result['^open']
            if open_data.get('err', 0) != 0:
                return ""

            file_id = open_data.get('fid')
            file_size = open_data.get('size', 0)

            if file_id is None or file_size == 0:
                return ""

            # Read file
            read_cmd = {"read": {"fid": file_id, "offset": 0, "length": file_size}}
            sequence = self._send_json_command(read_cmd)

            if sequence is None:
                return None

            response = self._wait_for_response(sequence)

            if not response or not response.get('binary'):
                return ""

            # Unpack and decode
            xml_data = self._unpack_7bit_to_8bit(response['binary'])
            return xml_data.decode('utf-8', errors='ignore')

        except Exception as e:
            logger.error(f'ERROR: USB fetch exception {e}')
            return None



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
    def __init__(self, control_surface):
        self.watchmsg = None
        self.finished = False
        self.control_surface = control_surface
        self.reset()

        try:
            self.fetcher = Fetcher(control_surface)
            # Start background thread for fetching and watching new saves
            _thread.start_new_thread(self.fetcher.start, (self,))
            logger.info('ThreadShare initialized with USB fetcher - background thread started')
        except Exception as e:
            logger.error(f'Error: unable to initialize fetcher {e}')

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


