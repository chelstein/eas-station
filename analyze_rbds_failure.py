#!/usr/bin/env python3
"""
Analyze actual RBDS CRC failures from diagnostic logs.

This will help determine if there's a systematic bit order issue.
"""

def calc_syndrome(x: int, mlen: int) -> int:
    """Calculate syndrome using RDS specification (Annex B)."""
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


def analyze_rbds_block(reg, block_num):
    """Analyze an RBDS block that failed CRC."""
    offset_word = [252, 408, 360, 436, 848]  # A, B, C, D, C'
    syndromes = [383, 14, 303, 663, 748]
    block_names = ['A', 'B', 'C', 'D', "C'"]
    
    # Extract dataword and checkword from register
    dataword = (reg >> 10) & 0xFFFF
    checkword = reg & 0x3FF
    
    # Calculate CRC on the dataword
    block_crc = calc_syndrome(dataword, 16)
    
    # Expected values for this block type
    offset_idx = block_num if block_num < 4 else 2
    expected_offset = offset_word[offset_idx]
    expected_syndrome = syndromes[offset_idx]
    
    # What we got from the XOR
    xor_result = checkword ^ expected_offset
    
    print(f"\n{'=' * 70}")
    print(f"Analyzing Block {block_names[block_num if block_num < 4 else 4]} (block_num={block_num})")
    print(f"{'=' * 70}")
    print(f"Register: 0x{reg:07X} ({reg:026b})")
    print(f"Dataword: 0x{dataword:04X} ({dataword:016b})")
    print(f"Checkword: 0x{checkword:03X} ({checkword:010b})")
    print(f"\nCRC Calculation:")
    print(f"  Calculated block_crc: {block_crc} (0x{block_crc:03X})")
    print(f"  Expected offset: {expected_offset} (0x{expected_offset:03X})")
    print(f"  checkword XOR offset: {xor_result} (0x{xor_result:03X})")
    print(f"  Match: {xor_result == block_crc}")
    
    # Try with bit-reversed dataword
    dataword_rev = reverse_bits(dataword, 16)
    block_crc_rev = calc_syndrome(dataword_rev, 16)
    xor_result_rev = checkword ^ expected_offset
    
    print(f"\nWith REVERSED dataword bits:")
    print(f"  Reversed dataword: 0x{dataword_rev:04X} ({dataword_rev:016b})")
    print(f"  Calculated block_crc: {block_crc_rev} (0x{block_crc_rev:03X})")
    print(f"  checkword XOR offset: {xor_result} (0x{xor_result:03X})")
    print(f"  Match: {xor_result == block_crc_rev}")
    
    # Try with reversed checkword
    checkword_rev = reverse_bits(checkword, 10)
    xor_result_ckrev = checkword_rev ^ expected_offset
    
    print(f"\nWith REVERSED checkword bits:")
    print(f"  Reversed checkword: 0x{checkword_rev:03X} ({checkword_rev:010b})")
    print(f"  Calculated block_crc: {block_crc} (0x{block_crc:03X})")
    print(f"  checkword_rev XOR offset: {xor_result_ckrev} (0x{xor_result_ckrev:03X})")
    print(f"  Match: {xor_result_ckrev == block_crc}")
    
    # Try with fully reversed register
    reg_rev = reverse_bits(reg, 26)
    dataword_regrev = (reg_rev >> 10) & 0xFFFF
    checkword_regrev = reg_rev & 0x3FF
    block_crc_regrev = calc_syndrome(dataword_regrev, 16)
    xor_result_regrev = checkword_regrev ^ expected_offset
    
    print(f"\nWith FULLY REVERSED register:")
    print(f"  Reversed register: 0x{reg_rev:07X} ({reg_rev:026b})")
    print(f"  Reversed dataword: 0x{dataword_regrev:04X}")
    print(f"  Reversed checkword: 0x{checkword_regrev:03X}")
    print(f"  Calculated block_crc: {block_crc_regrev} (0x{block_crc_regrev:03X})")
    print(f"  checkword XOR offset: {xor_result_regrev} (0x{xor_result_regrev:03X})")
    print(f"  Match: {xor_result_regrev == block_crc_regrev}")


if __name__ == "__main__":
    print("RBDS CRC Failure Analysis")
    print("="  * 70)
    print("Analyzing actual failed blocks from diagnostic logs...")
    
    # First few blocks from the log after sync at bit 34184
    # These are consecutive blocks that all failed CRC
    test_blocks = [
        # (register, block_num, expected_block_crc from log)
        (0x24CDAA1, 3, 847),   # Block D
        (0x00E4485, 0, 780),   # Block A
        (0x20C5E58, 1, 826),   # Block B
        (0x0251B87, 2, 925),   # Block C
    ]
    
    for reg, block_num, log_block_crc in test_blocks:
        analyze_rbds_block(reg, block_num)
        
    print(f"\n{'=' * 70}\n")
