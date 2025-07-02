#!/usr/bin/env python3
"""
DALConnector USB MIDI Test Script
==================================

This script tests the MIDI connection to the Deluge and verifies
that the required dependencies are installed correctly.

Usage: python3 test_midi_connection.py
"""

import sys

def test_imports():
    """Test if required MIDI libraries are installed."""
    print("Testing MIDI library imports...")
    
    try:
        import mido
        print("✓ mido library imported successfully")
        print(f"  Version: {mido.__version__}")
    except ImportError as e:
        print("✗ mido library not found!")
        print("  Install with: pip3 install mido")
        return False
    
    try:
        import rtmidi
        print("✓ python-rtmidi library imported successfully")
        print(f"  Version: {rtmidi.__version__}")
    except ImportError as e:
        print("✗ python-rtmidi library not found!")
        print("  Install with: pip3 install python-rtmidi")
        return False
    
    return True

def list_midi_ports():
    """List available MIDI input and output ports."""
    try:
        import mido
        
        print("\nAvailable MIDI Output Ports:")
        output_ports = mido.get_output_names()
        if output_ports:
            for i, port in enumerate(output_ports):
                print(f"  {i}: {port}")
        else:
            print("  No MIDI output ports found")
        
        print("\nAvailable MIDI Input Ports:")
        input_ports = mido.get_input_names()
        if input_ports:
            for i, port in enumerate(input_ports):
                print(f"  {i}: {port}")
        else:
            print("  No MIDI input ports found")
        
        return output_ports, input_ports
        
    except Exception as e:
        print(f"Error listing MIDI ports: {e}")
        return [], []

def test_deluge_connection():
    """Test if Deluge MIDI port is available."""
    try:
        import mido
        from DALConnector.config import DELUGE_MIDI_PORT_NAME
        
        print(f"\nTesting Deluge connection (looking for '{DELUGE_MIDI_PORT_NAME}')...")
        
        output_ports = mido.get_output_names()
        input_ports = mido.get_input_names()
        
        deluge_output_found = any(DELUGE_MIDI_PORT_NAME in port for port in output_ports)
        deluge_input_found = any(DELUGE_MIDI_PORT_NAME in port for port in input_ports)
        
        if deluge_output_found:
            print("✓ Deluge MIDI output port found")
        else:
            print("✗ Deluge MIDI output port not found")
        
        if deluge_input_found:
            print("✓ Deluge MIDI input port found")
        else:
            print("✗ Deluge MIDI input port not found")
        
        if deluge_output_found and deluge_input_found:
            print("✓ Deluge appears to be connected and ready!")
            return True
        else:
            print("✗ Deluge not detected. Make sure it's connected via USB.")
            return False
            
    except ImportError:
        print("Cannot test Deluge connection - config module not found")
        return False
    except Exception as e:
        print(f"Error testing Deluge connection: {e}")
        return False

def main():
    """Main test function."""
    print("DALConnector USB MIDI Connection Test")
    print("=====================================")
    
    # Test imports
    if not test_imports():
        print("\n✗ Required libraries not installed. Please run:")
        print("  pip3 install mido python-rtmidi")
        return 1
    
    # List MIDI ports
    output_ports, input_ports = list_midi_ports()
    
    # Test Deluge connection
    deluge_connected = test_deluge_connection()
    
    print("\n" + "="*50)
    if deluge_connected:
        print("✓ All tests passed! DALConnector should work.")
        print("\nNext steps:")
        print("1. Configure DALConnector in Ableton Live")
        print("2. Create a MIDI track with 'dc:' prefix")
        print("3. Test song loading from your Deluge")
    else:
        print("⚠ Some issues detected:")
        if not output_ports and not input_ports:
            print("- No MIDI ports found - check your audio drivers")
        if not deluge_connected:
            print("- Deluge not detected - check USB connection")
        print("\nTroubleshooting tips:")
        print("- Make sure your Deluge is powered on and connected via USB")
        print("- Try different USB ports or cables")
        print("- Check that your system recognizes the Deluge as a MIDI device")
    
    return 0 if deluge_connected else 1

if __name__ == "__main__":
    sys.exit(main())
