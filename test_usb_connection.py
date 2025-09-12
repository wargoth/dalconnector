#!/usr/bin/env python3
"""
Test script for DALConnector USB connection to Deluge.
This script tests the basic USB SysEx communication with a connected Deluge.
"""

import sys
import time
try:
    import rtmidi
except ImportError:
    print("ERROR: python-rtmidi not installed. Install with: pip install python-rtmidi")
    sys.exit(1)

class DelugeTester:
    DELUGE_SYSEX_HEADER = [0xF0, 0x00, 0x21, 0x7B, 0x01]
    SYSEX_END = 0xF7
    
    CMD_PING = 0x00
    CMD_PONG = 0x7F
    CMD_JSON = 0x04
    CMD_JSON_REPLY = 0x05
    
    def __init__(self):
        self.midi_out = None
        self.midi_in = None
        self.responses = {}
        
    def find_deluge_ports(self):
        """Find Deluge MIDI input/output ports"""
        try:
            midi_out = rtmidi.MidiOut()
            midi_in = rtmidi.MidiIn()
            
            out_ports = midi_out.get_ports()
            in_ports = midi_in.get_ports()
            
            print("Available MIDI Output Ports:")
            for i, port in enumerate(out_ports):
                print(f"  {i}: {port}")
                
            print("\nAvailable MIDI Input Ports:")
            for i, port in enumerate(in_ports):
                print(f"  {i}: {port}")
            
            deluge_out = None
            deluge_in = None
            
            for i, port_name in enumerate(out_ports):
                if 'Deluge' in port_name or 'deluge' in port_name.lower():
                    deluge_out = i
                    break
                    
            for i, port_name in enumerate(in_ports):
                if 'Deluge' in port_name or 'deluge' in port_name.lower():
                    deluge_in = i
                    break
                    
            if deluge_out is not None and deluge_in is not None:
                print(f"\nFound Deluge ports: OUT={deluge_out}, IN={deluge_in}")
                return deluge_out, deluge_in
            else:
                print("\nERROR: Deluge MIDI ports not found!")
                print("Make sure the Deluge is connected via USB and recognized as a MIDI device.")
                return None, None
                
        except Exception as e:
            print(f"Error finding MIDI ports: {e}")
            return None, None
            
    def connect(self):
        """Connect to Deluge MIDI ports"""
        out_port, in_port = self.find_deluge_ports()
        if out_port is None or in_port is None:
            return False
            
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_in = rtmidi.MidiIn()
            
            self.midi_out.open_port(out_port)
            self.midi_in.open_port(in_port)
            
            # Set up callback for incoming messages
            self.midi_in.set_callback(self._midi_callback)
            self.midi_in.ignore_types(False, False, False)  # Don't ignore SysEx
            
            print("Successfully connected to Deluge!")
            return True
            
        except Exception as e:
            print(f"Error connecting to Deluge: {e}")
            return False
            
    def _midi_callback(self, event, data):
        """Handle incoming MIDI messages"""
        message, deltatime = event
        
        # Check if it's a Deluge SysEx message
        if (len(message) >= 7 and 
            message[0] == 0xF0 and 
            message[1:5] == self.DELUGE_SYSEX_HEADER[1:5]):
            
            command = message[5]
            print(f"Received SysEx command: {command:02X}")
            
            if command == self.CMD_PONG:
                print("✓ Received PONG response!")
                self.responses['pong'] = True
            elif command == self.CMD_JSON_REPLY:
                print("✓ Received JSON reply!")
                self.responses['json'] = True
                
    def ping_test(self):
        """Test ping/pong communication"""
        print("\n=== Testing Ping/Pong ===")
        
        self.responses['pong'] = False
        ping_message = self.DELUGE_SYSEX_HEADER + [self.CMD_PING, self.SYSEX_END]
        
        print(f"Sending PING: {[hex(b) for b in ping_message]}")
        self.midi_out.send_message(ping_message)
        
        # Wait for response
        for i in range(50):  # 5 second timeout
            if self.responses.get('pong', False):
                print("✓ Ping test PASSED!")
                return True
            time.sleep(0.1)
            
        print("✗ Ping test FAILED - no response received")
        return False
        
    def json_test(self):
        """Test JSON file operation"""
        print("\n=== Testing JSON Communication ===")
        
        # Try to list SONGS directory
        import json
        
        self.responses['json'] = False
        command_dict = {"dir": {"path": "/SONGS", "offset": 0}}
        json_str = json.dumps(command_dict)
        json_bytes = [ord(c) & 0x7F for c in json_str]  # Ensure 7-bit clean
        
        message = (self.DELUGE_SYSEX_HEADER + 
                  [self.CMD_JSON, 1] +  # sequence number 1
                  json_bytes + 
                  [self.SYSEX_END])
                  
        print(f"Sending JSON command: {command_dict}")
        self.midi_out.send_message(message)
        
        # Wait for response
        for i in range(50):  # 5 second timeout
            if self.responses.get('json', False):
                print("✓ JSON test PASSED!")
                return True
            time.sleep(0.1)
            
        print("✗ JSON test FAILED - no response received")
        return False
        
    def disconnect(self):
        """Clean up MIDI connections"""
        if self.midi_in:
            self.midi_in.close_port()
        if self.midi_out:
            self.midi_out.close_port()

def main():
    print("DALConnector USB Connection Test")
    print("=" * 40)
    
    tester = DelugeTester()
    
    try:
        # Connect to Deluge
        if not tester.connect():
            return 1
            
        # Run tests
        ping_success = tester.ping_test()
        json_success = tester.json_test()
        
        print("\n" + "=" * 40)
        print("Test Results:")
        print(f"  Ping/Pong: {'PASS' if ping_success else 'FAIL'}")
        print(f"  JSON Comm: {'PASS' if json_success else 'FAIL'}")
        
        if ping_success and json_success:
            print("\n✓ All tests PASSED! USB connection is working correctly.")
            return 0
        else:
            print("\n✗ Some tests FAILED. Check your Deluge connection.")
            return 1
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        return 1
    finally:
        tester.disconnect()

if __name__ == "__main__":
    sys.exit(main())