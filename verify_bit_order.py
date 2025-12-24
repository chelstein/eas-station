#!/usr/bin/env python3
"""
Verify which bit shifting method is correct for MSB-first RBDS transmission.
"""

def test_bit_shifting():
    """Test both bit shifting approaches with known RBDS block."""

    # Known valid RBDS block (from test): 0x48D06A
    # Dataword: 0x1234, Checkword: 0x06A
    known_block = 0x48D06A

    # Convert to bit stream (MSB first transmission)
    bits = []
    for i in range(25, -1, -1):  # MSB (bit 25) first
        bits.append((known_block >> i) & 1)

    print("Testing RBDS Bit Order")
    print("=" * 70)
    print(f"Known valid block: 0x{known_block:07X}")
    print(f"Bit stream (MSB first): {bits[:8]}... (first 8 bits)")
    print()

    # Method 1: Shift LEFT and add at LSB (original code)
    reg1 = 0
    for bit in bits:
        reg1 = ((reg1 << 1) | bit) & 0x3FFFFFF

    print("Method 1: (reg << 1) | bit")
    print(f"  Result:   0x{reg1:07X}")
    print(f"  Expected: 0x{known_block:07X}")
    print(f"  Match: {'✓ CORRECT' if reg1 == known_block else '✗ WRONG'}")
    print()

    # Method 2: Shift RIGHT and add at MSB (commit 36944fa "fix")
    reg2 = 0
    for bit in bits:
        reg2 = ((bit << 25) | (reg2 >> 1)) & 0x3FFFFFF

    print("Method 2: (bit << 25) | (reg >> 1)")
    print(f"  Result:   0x{reg2:07X}")
    print(f"  Expected: 0x{known_block:07X}")
    print(f"  Match: {'✓ CORRECT' if reg2 == known_block else '✗ WRONG'}")
    print()

    # Show what method 2 actually produces
    print("Method 2 produces BIT-REVERSED block:")
    print(f"  0x{reg2:07X} = reversed bits of 0x{known_block:07X}")

    # Verify by reversing bits of known_block
    reversed_block = 0
    for i in range(26):
        if known_block & (1 << i):
            reversed_block |= 1 << (25 - i)
    print(f"  Bit reversal of 0x{known_block:07X} = 0x{reversed_block:07X}")
    print(f"  Method 2 result matches reversed: {'✓ YES' if reg2 == reversed_block else '✗ NO'}")
    print()
    print("=" * 70)
    print("CONCLUSION:")
    print("  Method 1 (original code) is CORRECT for MSB-first transmission")
    print("  Method 2 (commit 36944fa) REVERSES the bits - WRONG!")
    print("=" * 70)

if __name__ == "__main__":
    test_bit_shifting()
