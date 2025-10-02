from __future__ import absolute_import, print_function, unicode_literals

from ableton.v2.base import const, inject, listens
from ableton.v2.control_surface import ControlSurface

from .config import WATCH_FOR_NEW_SAVES
from .fetcher import ThreadShare
from .deluge2ableton import Deluge2Ableton
from .local import propername, displayname

from time import sleep
import Live
import logging
import time
import re

logger = logging.getLogger(__name__)

# Global SysEx interception flag
_SYSEX_INTERCEPTOR_INSTALLED = False

def install_global_sysex_interceptor():
    """Install global SysEx interceptor at module level"""
    global _SYSEX_INTERCEPTOR_INSTALLED
    if _SYSEX_INTERCEPTOR_INSTALLED:
        return

    try:
        # Try to patch at the ControlSurface level
        from ableton.v2.control_surface import ControlSurface

        if hasattr(ControlSurface, 'receive_midi'):
            original_receive_midi = ControlSurface.receive_midi
            logger.info("Installing global SysEx interceptor on ControlSurface.receive_midi")

            def global_receive_midi_interceptor(self, midi_bytes):
                logger.debug(f"GLOBAL INTERCEPTOR: {self.__class__.__name__} received {len(midi_bytes) if midi_bytes else 0} bytes")

                if midi_bytes and midi_bytes[0] == 0xF0:
                    logger.info(f"GLOBAL SysEx intercepted for {self.__class__.__name__}: {[hex(b) for b in midi_bytes[:10]]}")

                    # If this is our DALConnector instance, handle it
                    if isinstance(self, DALConnector) and hasattr(self, '_handle_sysex_message'):
                        logger.info("Routing SysEx to DALConnector handler")
                        self._handle_sysex_message(midi_bytes)
                        return

                # Call original method
                original_receive_midi(self, midi_bytes)

            ControlSurface.receive_midi = global_receive_midi_interceptor
            _SYSEX_INTERCEPTOR_INSTALLED = True
            logger.info("Global SysEx interceptor installed successfully")
        else:
            logger.warning("ControlSurface.receive_midi not found for global interception")

    except Exception as e:
        logger.error(f"Error installing global SysEx interceptor: {e}")
        import traceback
        logger.error(traceback.format_exc())


class DALConnector(ControlSurface):
    WATCH_INTERVAL_SLEEP = 10  # Wait time between polling, 20 is 2 seconds

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

    def __init__(self, *a, **k):
        super(DALConnector, self).__init__(*a, **k)

        # Request to receive all MIDI including SysEx
        self._do_receive_midi = True
        self._suppress_send_midi = False

        with self.component_guard():
            self.finished = False
            self.eventloopstarted = False

            self.ts = None
            logger.info(u'--- DAL Connector Started (USB SysEx Mode) ---')
            logger.info(f'Requesting SysEx delivery: _do_receive_midi={self._do_receive_midi}')

            # Install global SysEx interceptor
            install_global_sysex_interceptor()

            # Initialize USB fetcher
            self.ts = ThreadShare(self)

            self.__on_selected_track_name_changed.subject = self.song.view

            self._resetvars()



    def _on_received_midi(self, *midi_bytes):
        """Callback for received MIDI messages - receives bytes as individual arguments"""
        logger.info(f"_on_received_midi callback: {len(midi_bytes)} bytes")
        try:
            if midi_bytes and len(midi_bytes) > 0 and midi_bytes[0] == 0xF0:
                logger.info(f"SysEx via callback: {[hex(b) for b in midi_bytes[:20]]}")
                # Forward to fetcher for processing
                if self.ts and hasattr(self.ts, 'fetcher'):
                    self.ts.fetcher.handle_sysex_response(list(midi_bytes))
        except Exception as e:
            logger.error(f"Error in _on_received_midi: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def receive_midi(self, midi_bytes):
        """Handle incoming MIDI messages including SysEx"""
        logger.debug(f"receive_midi called with {len(midi_bytes) if midi_bytes else 0} bytes")
        try:
            if midi_bytes and midi_bytes[0] == 0xF0:  # SysEx message
                logger.info(f"Received SysEx message: {[hex(b) for b in midi_bytes[:10]]}")
                self._handle_sysex_message(midi_bytes)
                return  # Don't call parent for SysEx messages we handle
            else:
                # Let parent handle other MIDI messages
                super(DALConnector, self).receive_midi(midi_bytes)
        except Exception as e:
            logger.error(f"Error processing MIDI: {e}")
            import traceback
            logger.error(traceback.format_exc())


    def build_midi_map(self, midi_map_handle):
        """Request SysEx messages from Ableton"""
        logger.info("build_midi_map called - requesting SysEx delivery")

        # Register for Deluge SysEx messages
        # Deluge manufacturer ID: 0x00 0x21 0x7B
        try:
            from ableton.v2.control_surface.elements import SysexElement

            # Register a SysEx listener for Deluge messages
            # Header: F0 00 21 7B 01 (Deluge SysEx header)
            sysex_identifier = (0xF0, 0x00, 0x21, 0x7B, 0x01)

            logger.info(f"Registering SysEx identifier: {[hex(b) for b in sysex_identifier]}")

            # Add listener for received MIDI
            if not self.received_midi_has_listener(self._on_received_midi):
                self.add_received_midi_listener(self._on_received_midi)
                logger.info("Added received MIDI listener")

        except Exception as e:
            logger.error(f"Error registering SysEx: {e}")
            import traceback
            logger.error(traceback.format_exc())

        super(DALConnector, self).build_midi_map(midi_map_handle)
        logger.info("build_midi_map completed")

    def suggest_input_port(self):
        """Suggest input port for Deluge"""
        logger.info("suggest_input_port called")
        return str("Deluge")

    def suggest_output_port(self):
        """Suggest output port for Deluge"""
        logger.info("suggest_output_port called")
        return str("Deluge")

    def can_lock_to_devices(self):
        """Indicate that we don't lock to devices"""
        return False

    def handle_sysex(self, midi_bytes):
        """Handle SysEx messages from Ableton's routing"""
        logger.info(f"handle_sysex called with {len(midi_bytes) if midi_bytes else 0} bytes")
        if midi_bytes and self.ts and hasattr(self.ts, 'fetcher'):
            logger.info(f"SysEx via handle_sysex: {[hex(b) for b in midi_bytes[:20]]}")
            self.ts.fetcher.handle_sysex_response(list(midi_bytes))

    def disconnect(self):
        self.finished = True

        # Remove MIDI listener
        if self.received_midi_has_listener(self._on_received_midi):
            self.remove_received_midi_listener(self._on_received_midi)

        if self.ts:
            self.ts.disconnect()

        self._resetvars()


    @listens(u'selected_track.name')
    def __on_selected_track_name_changed(self):
        track = self.song.view.selected_track

        if self.targettrack and track != self.targettrack:
            return

        if not track.name.lower().startswith('dc:'):
            if self.targettrack and track == self.targettrack:
                self._resetvars()

            return

        if track.name.endswith(']'):
            return

        self.targettrack = track

        self.schedule_message(1, self.handletrackchange)

    def handletrackchange(self):
        view = self.song.view
        track = view.selected_track

        num = re.search(r'^dc: *(\d+[a-z]*)', track.name, re.IGNORECASE)
        if not num:
            # logger.info(u'ERR!  Invalid song number specified')
            return
        else:
            self.delugesong = propername(num.groups()[0])

        # logger.info(f'Deluge song is {self.delugesong}')

        # Fetch song using USB SysEx
        self.ts.fetchsong(self.delugesong)
        self._addtrackmsg(f'[fetching...]')
        self.expectsong = self.delugesong

        if not self.eventloopstarted:
            self.eventloopstarted = True
            self.schedule_message(10, self.eventloop)


    def eventloop(self):
        if self.finished:
            return

        try:
            if self.ts is None:
                return

            if self.expectsong is None:
                if not WATCH_FOR_NEW_SAVES:
                    return

                nextsongdata = self.ts.getnextsongdata()

                if nextsongdata is not None:
                    self.delugesong = nextsongdata['delugesong']
                    # logger.info(f'[EVENT LOOP]: LOADING NEXT SONG!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                    self.loadsong(nextsongdata['songhsh'])

                value = self.ts.getwatchmsg()
                if value:
                    self._addtrackmsg(f'[{value}]')

                return

            value = self.ts.getwatchmsg()
            if value:
                self._addtrackmsg(f'[{value}]')

            self.expecttries += 1

            if self.expecttries > 60:
                self.expecttries = 0
                self.expectsong = None

                self._addtrackmsg('[error 5]')
                logger.info(f'Expected song never showed up!')
                return

            result = self.ts.getresult(self.expectsong)

            if result is not None:
                self.expecttries = 0
                self.expectsong = None

                if result['error']:
                    self._addtrackmsg('[error 2]')
                    return

                self.loadsong(result['songhsh'])

                if not WATCH_FOR_NEW_SAVES:
                    self._addtrackmsg('[synced]')

                return

        finally:
            self.schedule_message(10, self.eventloop)

    def _addtrackmsg(self, msg):
        if self.targettrack is None:
            return

        name = f'dc: {displayname(self.delugesong)} {msg.strip()}'

        self.targettrack.name = name


    def _ensureenoughscenes(self, numscenes):
        numscenes += 1

        if len(self.song.scenes) >= numscenes:
            return

        for i in range(0, numscenes - len(self.song.scenes)):
            self.song.create_scene(-1)


    def _ensureenoughtracks(self, numtracks):
        tracks = self.song.visible_tracks

        index = list(tracks).index(self.targettrack)

        allslots = []
        count = 0
        for i in range(index, len(tracks)):
            track = tracks[i]

            if track.has_midi_input:
                count += 1

                # CLEAR THE SLOTS
                for s in range(0, len(self.song.scenes)):
                    slot = track.clip_slots[s]

                    if not slot.has_clip:
                        continue

                    allslots.append(slot)
                    slot.clip.remove_notes_extended(from_time = 0, from_pitch = 0, time_span = slot.clip.loop_end, pitch_span = 128)
            else:
                break

        if count < numtracks:
            for i in range(0, numtracks - count):
                self.song.create_midi_track()

        return allslots


    def loadsong(self, songhsh):
        bpm = songhsh['bpm']
        numscenes = songhsh['numscenes']
        maxtrackid = songhsh['maxtrackid']
        clipmap = songhsh['clipmap']

        self.song.tempo = bpm

        self._ensureenoughscenes(numscenes)              # We need this many scenes
        allslots = self._ensureenoughtracks(maxtrackid)  # We need this many midi tracks

        tracks = self._addressabletracks()

        for cliphsh in clipmap:

            trackidx = cliphsh['trackidx']
            track = tracks[trackidx]

            sceneidx = cliphsh['sceneidx']
            length = cliphsh['length']

            # logger.info(f'CREATE CLIP: SCENEIDX: {sceneidx}  TrackIDX: {trackidx}')

            slot = track.clip_slots[sceneidx]
            if slot.has_clip:
                if slot.clip.length != length:
                    slot.delete_clip()
                    slot.create_clip(length)
            else:
                slot.create_clip(length)

            notes = cliphsh['notes']

            result = []
            for hsh in notes:

                result.append(Live.Clip.MidiNoteSpecification(
                    pitch = hsh['pitch'],
                    start_time = hsh['starttime'],
                    duration = hsh['duration'],
                    velocity = hsh['velocity'],
                    mute = 0,
                    probability = hsh['probability']
                    ))

            slot.clip.add_new_notes(result)

            # We used the clip
            if slot in allslots:
                allslots.remove(slot)


        # If we didn't use the clip, remove it
        for slot in allslots:
            slot.delete_clip()


    def _addressabletracks(self):
        tracks = self.song.visible_tracks

        index = list(tracks).index(self.targettrack)

        result = []
        for i in range(index, len(tracks)):
            if not tracks[i].has_midi_input:
                continue

            result.append(tracks[i])

        return result


    def _resetvars(self):
        self.delugesong = None      # SONG000.XML
        self.targettrack = None     # Which track is titled dc:
        self.watchfor = None        # The name of the new save we're watching for

        self.expecttries = 0
        self.expectsong = None

