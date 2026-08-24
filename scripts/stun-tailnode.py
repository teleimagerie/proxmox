#!/usr/bin/env python3
"""Sonde STUN imitant un client Tailscale : SOFTWARE="tailnode" + FINGERPRINT.
Le STUN embarque de headscale/derper ignore silencieusement tout le reste
(voir 11-headscale.md, section Diagnostic).
Usage: stun-tailnode.py <hote> [port]"""
import binascii, socket, struct, sys

host = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 3478

tid = b"ClaudeTest12"
software = b"tailnode"                       # 8 octets, pas de padding requis
attrs = struct.pack(">HH8s", 0x8022, len(software), software)
total_len = len(attrs) + 8                   # + attribut FINGERPRINT (4+4)
msg = struct.pack(">HHI12s", 0x0001, total_len, 0x2112A442, tid) + attrs
crc = (binascii.crc32(msg) ^ 0x5354554E) & 0xFFFFFFFF
msg += struct.pack(">HHI", 0x8028, 4, crc)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(4)
s.sendto(msg, (host, port))
try:
    data, addr = s.recvfrom(1024)
    print(f"OK: reponse STUN de {addr}, {len(data)} octets")
except socket.timeout:
    print("TIMEOUT")
    sys.exit(1)
