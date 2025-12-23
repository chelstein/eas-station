#!/usr/bin/env python3
"""Check if our CRC calculation matches what the log shows."""

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

# From logs
test_blocks = [
    (0x24CDAA1, 0x9336, 847),
    (0x00E4485, 0x0391, 780),
    (0x20C5E58, 0x8317, 826),
    (0x0251B87, 0x0946, 925),
]

print("Verifying block_crc calculations match logs:")
for reg, dataword, log_crc in test_blocks:
    calc_crc = calc_syndrome(dataword, 16)
    extracted_dataword = (reg >> 10) & 0xFFFF
    print(f"Reg 0x{reg:07X}: dataword=0x{dataword:04X}, extracted=0x{extracted_dataword:04X}, log_crc={log_crc}, calc_crc={calc_crc}, match={calc_crc == log_crc}")
