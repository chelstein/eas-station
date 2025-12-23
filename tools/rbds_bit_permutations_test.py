#!/usr/bin/env python3
"""
Test all possible bit permutations to find the correct RBDS decoding.

This script tests:
1. Normal differential decoding vs. inverted
2. Normal bit polarity vs. inverted (all bits flipped)
3. Normal bit order vs. reversed (within 26-bit blocks)
4. Combinations of the above

Purpose: After 30 PRs, we need to systematically test EVERY possibility.
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


def test_permutation(bits, diff_inv=False, bit_inv=False, bit_rev=False):
    """Test a specific permutation of bit processing.
    
    Args:
        bits: List of raw symbols (0 or 1)
        diff_inv: If True, invert differential decoding (same=1 instead of different=1)
        bit_inv: If True, invert all bits after differential (0->1, 1->0)
        bit_rev: If True, reverse bits within each 26-bit block
    
    Returns:
        (syndrome, description)
    """
    # Step 1: Differential decoding
    diff_bits = []
    for i in range(1, len(bits)):
        if diff_inv:
            # Inverted: same = 1, different = 0
            diff_bits.append(1 if bits[i] == bits[i-1] else 0)
        else:
            # Normal: different = 1, same = 0
            diff_bits.append(1 if bits[i] != bits[i-1] else 0)
    
    # Step 2: Bit inversion
    if bit_inv:
        diff_bits = [1 - b for b in diff_bits]
    
    # Step 3: Build 26-bit blocks
    if len(diff_bits) < 26:
        return (None, "Not enough bits")
    
    # Take first 26 bits
    block_bits = diff_bits[:26]
    
    # Step 4: Bit reversal within block
    if bit_rev:
        block_bits = list(reversed(block_bits))
    
    # Step 5: Convert to integer (MSB first)
    block = 0
    for bit in block_bits:
        block = (block << 1) | bit
    
    # Step 6: Calculate syndrome
    syndrome = calc_syndrome(block, 26)
    
    desc = f"diff_inv={diff_inv}, bit_inv={bit_inv}, bit_rev={bit_rev}"
    return (syndrome, desc)


def main():
    # Target syndromes for RBDS block types
    target_syndromes = {
        383: 'A',
        14: 'B',
        303: 'C',
        663: 'D',
        748: "C'"
    }
    
    # Simulate some received symbols (example)
    # In reality, these would come from the demodulator
    # For this test, let's create a known valid block
    print("=" * 70)
    print("RBDS Bit Permutation Test")
    print("=" * 70)
    print()
    print("Testing all permutations of bit processing...")
    print()
    
    # Create a known valid Block A (PI code 0x1234)
    dataword = 0x1234
    syndrome_calc = calc_syndrome(dataword, 16)
    checkword = syndrome_calc ^ 0x0FC  # Block A offset
    block = (dataword << 10) | checkword
    
    # Convert block to bits (MSB first)
    correct_bits = []
    for i in range(25, -1, -1):
        correct_bits.append((block >> i) & 1)
    
    # Add a fake "previous symbol" for differential encoding
    # Assume previous symbol was 0
    symbols = [0]
    
    # Simulate transmitter differential encoding
    # Rule: if bit=1, flip phase; if bit=0, keep phase
    current_phase = 0
    for bit in correct_bits:
        if bit == 1:
            current_phase = 1 - current_phase  # Flip
        symbols.append(current_phase)
    
    print(f"Generated {len(symbols)} symbols from known valid Block A")
    print(f"  Expected PI code: 0x{dataword:04X}")
    print(f"  Expected syndrome: 383 (Block A)")
    print()
    
    # Test all 8 permutations (2^3)
    print("Testing all 8 permutations:")
    print()
    
    results = []
    for diff_inv in [False, True]:
        for bit_inv in [False, True]:
            for bit_rev in [False, True]:
                syndrome, desc = test_permutation(symbols, diff_inv, bit_inv, bit_rev)
                results.append((syndrome, desc, diff_inv, bit_inv, bit_rev))
                
                status = ""
                if syndrome in target_syndromes:
                    status = f" ← MATCH! Block {target_syndromes[syndrome]}"
                
                print(f"  {desc:50s} → syndrome={syndrome}{status}")
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    matches = [r for r in results if r[0] in target_syndromes]
    if matches:
        print(f"\n✓ Found {len(matches)} matching configuration(s):")
        for syndrome, desc, diff_inv, bit_inv, bit_rev in matches:
            block_type = target_syndromes[syndrome]
            print(f"\n  Block {block_type} (syndrome={syndrome}):")
            print(f"    Differential inverted: {diff_inv}")
            print(f"    Bits inverted: {bit_inv}")
            print(f"    Bits reversed: {bit_rev}")
    else:
        print("\n✗ No matching configuration found!")
        print("  This suggests a more fundamental issue with the signal processing.")
    
    print()


if __name__ == "__main__":
    main()
