#!/usr/bin/env python3
"""Test if reversing the bit order within 26-bit blocks helps."""

def calc_syndrome(x: int, mlen: int) -> int:
    """Calculate syndrome using RDS specification."""
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
    """Reverse the bit order."""
    result = 0
    for i in range(num_bits):
        if x & (1 << i):
            result |= 1 << (num_bits - 1 - i)
    return result


# Test with actual failed blocks
# These are after sync at bit 34184, block sequence should be 3,0,1,2,3...
test_blocks = [
    # (register, expected_block_num, block_name)
    (0x24CDAA1, 3, "D"),   # First block after sync
    (0x00E4485, 0, "A"),
    (0x20C5E58, 1, "B"),
    (0x0251B87, 2, "C"),
]

syndromes = [383, 14, 303, 663, 748]  # A, B, C, D, C'
offset_word = [252, 408, 360, 436, 848]

print("Testing if bit-reversing the 26-bit block helps:")
print("=" * 70)

for reg, block_num, block_name in test_blocks:
    # Calculate syndrome of normal block
    syndrome_normal = calc_syndrome(reg, 26)
    
    # Calculate syndrome of bit-reversed block
    reg_reversed = reverse_bits(reg, 26)
    syndrome_reversed = calc_syndrome(reg_reversed, 26)
    
    # Expected syndrome for this block type
    expected = syndromes[block_num] if block_num < 4 else syndromes[2]
    
    print(f"\nBlock {block_name} (block_num={block_num}):")
    print(f"  Original reg: 0x{reg:07X}")
    print(f"  Normal syndrome: {syndrome_normal} (0x{syndrome_normal:03X}), expected: {expected}")
    print(f"  Match: {'✓ YES' if syndrome_normal == expected else '✗ NO'}")
    print(f"  Reversed reg: 0x{reg_reversed:07X}")
    print(f"  Reversed syndrome: {syndrome_reversed} (0x{syndrome_reversed:03X}), expected: {expected}")
    print(f"  Match: {'✓ YES' if syndrome_reversed == expected else '✗ NO'}")
    
    # Also check if the reversed syndrome matches ANY target
    for i, target in enumerate(syndromes):
        if syndrome_reversed == target:
            print(f"  ⚠️  Reversed syndrome matches Block {['A','B','C','D','C'][i]}!")

print("\n" + "=" * 70)
