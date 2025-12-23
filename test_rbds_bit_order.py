#!/usr/bin/env python3
"""
Test RBDS bit order and CRC calculation.

This script tests if there's a bit order issue in RBDS decoding by:
1. Creating a known valid RBDS block
2. Testing CRC calculation with normal and reversed bit orders
3. Comparing against expected syndrome values
"""

def calc_syndrome(x: int, mlen: int) -> int:
    """Calculate syndrome using RDS specification (Annex B).
    
    Uses polynomial g(x) = x^10 + x^8 + x^7 + x^5 + x^4 + x^3 + 1 = 0x5B9
    This processes bits from MSB to LSB.
    """
    reg = 0
    plen = 10
    for ii in range(mlen, 0, -1):
        reg = (reg << 1) | ((x >> (ii - 1)) & 0x01)
        if reg & (1 << plen):
            reg = reg ^ 0x5B9
    for ii in range(plen, 0, -1):
        reg = reg << 1
        if reg & (1 << plen):
            reg = reg ^ 0x5B9
    return reg & ((1 << plen) - 1)


def reverse_bits(x: int, num_bits: int) -> int:
    """Reverse the bit order of an integer."""
    result = 0
    for i in range(num_bits):
        if x & (1 << i):
            result |= 1 << (num_bits - 1 - i)
    return result


def test_known_rbds_block():
    """Test with a known valid RBDS block structure."""
    print("=" * 70)
    print("RBDS Bit Order Test")
    print("=" * 70)
    
    # RDS specification test values
    # Block A offset word: 0x0FC (252 decimal)
    # Expected syndrome when dataword is all zeros: 383
    offset_word_A = 0x0FC
    
    # Test 1: Zero dataword (16 bits) + offset (10 bits) = 26 bits
    # In a valid block, the 10-bit checkword equals: calc_syndrome(dataword, 16) XOR offset
    dataword = 0x0000
    syndrome = calc_syndrome(dataword, 16)
    checkword = syndrome ^ offset_word_A
    
    # Build 26-bit block: dataword (16 MSB) | checkword (10 LSB)
    block_normal = (dataword << 10) | checkword
    
    print(f"\nTest 1: Zero dataword")
    print(f"  Dataword: 0x{dataword:04X} ({dataword})")
    print(f"  Calculated syndrome: {syndrome} (0x{syndrome:03X})")
    print(f"  Expected syndrome for Block A: 383 (0x17F)")
    print(f"  Checkword: 0x{checkword:03X} ({checkword})")
    print(f"  26-bit block: 0x{block_normal:07X}")
    print(f"  Match: {'✓ PASS' if syndrome == 383 else '✗ FAIL'}")
    
    # Test 2: Verify syndrome calculation on the full 26-bit block
    block_syndrome = calc_syndrome(block_normal, 26)
    print(f"\nTest 2: Syndrome of full block")
    print(f"  Full block syndrome: {block_syndrome} (0x{block_syndrome:03X})")
    print(f"  Expected: 383 (0x17F) for Block A")
    print(f"  Match: {'✓ PASS' if block_syndrome == 383 else '✗ FAIL'}")
    
    # Test 3: Try with reversed bit order
    block_reversed = reverse_bits(block_normal, 26)
    block_rev_syndrome = calc_syndrome(block_reversed, 26)
    print(f"\nTest 3: Reversed bit order")
    print(f"  Reversed block: 0x{block_reversed:07X}")
    print(f"  Syndrome: {block_rev_syndrome} (0x{block_rev_syndrome:03X})")
    print(f"  Match: {'✓ PASS' if block_rev_syndrome == 383 else '✗ FAIL'}")
    
    # Test 4: Test with actual PI code (common value 0x1234)
    print(f"\n{'=' * 70}")
    print("Test 4: Realistic Block A with PI code")
    print("=" * 70)
    dataword = 0x1234  # Example PI code
    syndrome = calc_syndrome(dataword, 16)
    checkword = syndrome ^ offset_word_A
    block_normal = (dataword << 10) | checkword
    block_syndrome = calc_syndrome(block_normal, 26)
    
    print(f"  PI Code (dataword): 0x{dataword:04X}")
    print(f"  Checkword: 0x{checkword:03X}")
    print(f"  Full block: 0x{block_normal:07X}")
    print(f"  Block syndrome: {block_syndrome} (0x{block_syndrome:03X})")
    print(f"  Expected: 383 (0x17F)")
    print(f"  Match: {'✓ PASS' if block_syndrome == 383 else '✗ FAIL'}")
    
    # Test 5: Verify CRC check logic
    print(f"\n{'=' * 70}")
    print("Test 5: CRC Check Logic")
    print("=" * 70)
    received_dataword = (block_normal >> 10) & 0xFFFF
    received_checkword = block_normal & 0x3FF
    calculated_crc = calc_syndrome(received_dataword, 16)
    
    print(f"  Received dataword: 0x{received_dataword:04X}")
    print(f"  Received checkword: 0x{received_checkword:03X}")
    print(f"  Calculated CRC: {calculated_crc} (0x{calculated_crc:03X})")
    print(f"  Offset word: {offset_word_A} (0x{offset_word_A:03X})")
    print(f"  checkword XOR offset: {received_checkword ^ offset_word_A}")
    print(f"  CRC match: {(received_checkword ^ offset_word_A) == calculated_crc}")
    
    # Test 6: Check all block types
    print(f"\n{'=' * 70}")
    print("Test 6: All Block Type Syndromes")
    print("=" * 70)
    
    block_info = [
        ("A", 0x0FC, 383),
        ("B", 0x198, 14),
        ("C", 0x168, 303),
        ("D", 0x1B4, 663),
        ("C'", 0x350, 748),
    ]
    
    for block_name, offset, expected_syndrome in block_info:
        dataword = 0x0000
        syndrome = calc_syndrome(dataword, 16)
        checkword = syndrome ^ offset
        block = (dataword << 10) | checkword
        block_syndrome = calc_syndrome(block, 26)
        status = "✓ PASS" if block_syndrome == expected_syndrome else "✗ FAIL"
        print(f"  Block {block_name:2s}: syndrome={block_syndrome:3d} (0x{block_syndrome:03X}), expected={expected_syndrome:3d} - {status}")


if __name__ == "__main__":
    test_known_rbds_block()
    print(f"\n{'=' * 70}\n")
