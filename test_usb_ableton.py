#!/usr/bin/env python3
"""
Test script for DALConnector USB connection using Ableton's MIDI framework.
This script demonstrates how to test the USB functionality within Ableton Live.

IMPORTANT: This script is designed to run within Ableton Live's Python environment
as part of a control surface script, not as a standalone script.
"""

import logging

# Set up logging to see test results in Ableton's log
logger = logging.getLogger('DALConnector.test')

def test_usb_connection_in_ableton(control_surface):
    """
    Test USB connection to Deluge within Ableton Live environment.

    Args:
        control_surface: The Ableton ControlSurface instance

    Usage:
        1. Install DALConnector as a control surface in Ableton
        2. Add this test to the DALConnector.py file and call it
        3. Check Ableton's log file for results

    Example integration in DALConnector.py:
        def __init__(self, *a, **k):
            super(DALConnector, self).__init__(*a, **k)
            # ... existing code ...

            # Run USB test
            from .test_usb_ableton import test_usb_connection_in_ableton
            test_usb_connection_in_ableton(self)
    """

    logger.info("=== DALConnector USB Test (Ableton Framework) ===")

    try:
        from .usb_fetcher import USBFetcher

        # Create USB fetcher with control surface
        usb_fetcher = USBFetcher(control_surface)

        logger.info("✓ USBFetcher created successfully")

        # Test ping command
        logger.info("Testing ping to Deluge...")

        if usb_fetcher._ping_deluge():
            logger.info("✓ Ping test PASSED - Deluge responded!")

            # Test JSON command
            logger.info("Testing JSON command...")
            test_command = {"ping": {}}
            sequence = usb_fetcher._send_json_command(test_command)

            if sequence:
                logger.info(f"✓ JSON command sent with sequence {sequence}")

                # Wait for response
                response = usb_fetcher._wait_for_response(sequence)
                if response:
                    logger.info("✓ JSON test PASSED - received response!")
                    logger.info(f"Response: {response}")
                else:
                    logger.warning("✗ JSON test FAILED - no response received")
            else:
                logger.error("✗ Failed to send JSON command")

        else:
            logger.error("✗ Ping test FAILED - no response from Deluge")
            logger.error("Check that:")
            logger.error("1. Deluge is connected via USB")
            logger.error("2. Deluge MIDI ports are assigned to DALConnector in Ableton preferences")
            logger.error("3. Deluge is powered on and in USB MIDI mode")

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        logger.error("Make sure Deluge is connected and DALConnector is properly configured")

    logger.info("=== USB Test Complete ===")

def manual_test_instructions():
    """
    Instructions for manually testing USB functionality in Ableton.
    """
    instructions = """
    MANUAL USB TEST INSTRUCTIONS:

    1. SETUP:
       - Connect Deluge via USB to computer
       - Ensure Deluge is powered on
       - Open Ableton Live

    2. CONFIGURE ABLETON:
       - Go to Preferences > Link/Tempo/MIDI
       - In Control Surface section, select DALConnector
       - Set Input to "Deluge" (should appear in list)
       - Set Output to "Deluge" (should appear in list)

    3. TEST CONNECTION:
       - Create a MIDI track in Ableton
       - Name it "dc:1a" (requests song SONG001A.XML from Deluge)
       - Select the track
       - Check Ableton's log file for connection messages

    4. EXPECTED BEHAVIOR:
       - Track name changes to "dc:1a [fetching...]"
       - USB communication begins automatically
       - Song data loads from Deluge if file exists
       - Track name updates to show status

    5. TROUBLESHOOTING:
       - Check Ableton log: Help > Open Log File
       - Look for DALConnector USB messages
       - Verify Deluge appears in MIDI device list
       - Try different USB cable/port if issues persist

    6. LOG FILE LOCATION:
       - Windows: %USERPROFILE%\\AppData\\Roaming\\Ableton\\Live 11 Suite\\Preferences\\Log.txt
       - macOS: ~/Library/Preferences/Ableton/Live 11 Suite/Log.txt
    """
    return instructions

if __name__ == "__main__":
    print("This test script is designed to run within Ableton Live.")
    print("It cannot run standalone - integration required with DALConnector.")
    print()
    print(manual_test_instructions())