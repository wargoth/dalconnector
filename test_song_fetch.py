#!/usr/bin/env python3
"""
DALConnector Song Fetch Test
============================

This script tests the song fetching functionality using the DelugeWeb protocol
to read XML files directly from the Deluge's SONGS directory.

Usage: python3 test_song_fetch.py [song_number]
Example: python3 test_song_fetch.py 001
"""

import sys
import logging
from DALConnector.fetcher import Fetcher

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_song_fetch(song_number="001"):
    """Test fetching a specific song"""
    print(f"Testing song fetch for song: {song_number}")
    
    try:
        # Create fetcher instance
        fetcher = Fetcher()
        
        # Attempt to fetch the song
        print(f"Attempting to fetch song {song_number}...")
        xml_data = fetcher.fetch(song_number)
        
        if xml_data:
            print(f"✓ Successfully fetched song {song_number}")
            print(f"  XML length: {len(xml_data)} characters")
            print(f"  First 200 characters: {xml_data[:200]}...")
            
            # Try to parse with Deluge2Ableton converter
            from DALConnector.deluge2ableton import Deluge2Ableton
            try:
                song_data = Deluge2Ableton.convert(xml_data)
                print(f"✓ Successfully converted to Ableton format")
                print(f"  BPM: {song_data.get('bpm', 'unknown')}")
                print(f"  Scenes: {song_data.get('numscenes', 'unknown')}")
                print(f"  Tracks: {song_data.get('maxtrackid', 'unknown')}")
                print(f"  Clips: {len(song_data.get('clipmap', []))}")
            except Exception as e:
                print(f"✗ Failed to convert XML to Ableton format: {e}")
        else:
            print(f"✗ Failed to fetch song {song_number}")
            print("  Possible causes:")
            print("  - Song file doesn't exist on Deluge")
            print("  - MIDI connection issues")
            print("  - Protocol implementation needs refinement")
        
        return xml_data is not None
        
    except Exception as e:
        print(f"✗ Error during song fetch test: {e}")
        return False

def main():
    """Main test function"""
    song_number = "001"
    
    if len(sys.argv) > 1:
        song_number = sys.argv[1].zfill(3)  # Pad to 3 digits
    
    print("DALConnector Song Fetch Test")
    print("============================")
    print(f"Testing with song: {song_number}")
    print()
    
    success = test_song_fetch(song_number)
    
    print()
    print("Test Results:")
    print("=============")
    if success:
        print("✓ Song fetch test PASSED")
        print("The DelugeWeb protocol implementation appears to be working!")
    else:
        print("✗ Song fetch test FAILED")
        print("Check the log output above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
