"""XEX2 container reading shared by tools/extract_pkg.py and tools/survey_pe.py.

Field layouts follow Xenia's public headers (github.com/xenia-project/xenia,
src/xenia/kernel/util/xex2_info.h and src/xenia/cpu/xex_module.cc). Every
integer in the container is big-endian.

Only what this project's target needs is handled: an AES-encrypted image with
"basic" compression (runs of stored bytes followed by runs of zeros). Anything
else is refused with a message that names it.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

# The retail XEX2 key: one AES-128 constant shared by every retail title,
# which unwraps the per-file session key held in the security info. It is
# published in Xenia's source as `xe_xex2_retail_key`
# (src/xenia/cpu/xex_module.cc); docs/LEGAL.md records why it is here.
XEX2_RETAIL_KEY = bytes.fromhex("20B185A59D28FDC340583FBB0896BF91")

# Optional header keys (xex2_header_keys in xex2_info.h).
KEY_RESOURCE_INFO = 0x000002FF
KEY_FILE_FORMAT_INFO = 0x000003FF
KEY_ENTRY_POINT = 0x00010100
KEY_IMAGE_BASE_ADDRESS = 0x00010201
KEY_IMPORT_LIBRARIES = 0x000103FF
KEY_CHECKSUM_TIMESTAMP = 0x00018002
KEY_ORIGINAL_PE_NAME = 0x000183FF
KEY_STATIC_LIBRARIES = 0x000200FF
KEY_DEFAULT_STACK_SIZE = 0x00020200
KEY_EXECUTION_INFO = 0x00040006

ENCRYPTION_NONE, ENCRYPTION_NORMAL = 0, 1
COMPRESSION_NONE, COMPRESSION_BASIC, COMPRESSION_NORMAL, COMPRESSION_DELTA = 0, 1, 2, 3

# Offsets inside the security info (xex2_security_info).
SEC_IMAGE_SIZE = 0x004
SEC_LOAD_ADDRESS = 0x110
SEC_AES_KEY = 0x150


class XexError(Exception):
    pass


@dataclass
class ImportLibrary:
    name: str
    version: tuple[int, int, int, int]
    version_min: tuple[int, int, int, int]
    records: list[int] = field(default_factory=list)   # addresses in the image


@dataclass
class Xex:
    data: bytes
    module_flags: int
    pe_data_offset: int
    security_offset: int
    opt: dict[int, int]            # key -> raw value (immediate or offset)

    # ---- optional headers -------------------------------------------------
    def opt_value(self, key: int) -> int | None:
        return self.opt.get(key)

    def opt_bytes(self, key: int, n: int | None = None) -> bytes | None:
        """The data of an optional header whose value is an offset. Keys whose
        low byte is 0xFF carry their own size in the first word."""
        off = self.opt.get(key)
        if off is None:
            return None
        if n is None:
            (n,) = struct.unpack_from(">I", self.data, off)
        return self.data[off:off + n]

    # ---- security info ----------------------------------------------------
    @property
    def image_size(self) -> int:
        return struct.unpack_from(">I", self.data, self.security_offset + SEC_IMAGE_SIZE)[0]

    @property
    def load_address(self) -> int:
        return struct.unpack_from(">I", self.data, self.security_offset + SEC_LOAD_ADDRESS)[0]

    @property
    def wrapped_key(self) -> bytes:
        o = self.security_offset + SEC_AES_KEY
        return self.data[o:o + 16]

    # ---- simple headers ---------------------------------------------------
    @property
    def entry_point(self) -> int | None:
        return self.opt.get(KEY_ENTRY_POINT)

    @property
    def image_base(self) -> int | None:
        return self.opt.get(KEY_IMAGE_BASE_ADDRESS)

    @property
    def original_pe_name(self) -> str | None:
        b = self.opt_bytes(KEY_ORIGINAL_PE_NAME)
        return None if b is None else b[4:].split(b"\0", 1)[0].decode("ascii")

    def execution_info(self) -> dict | None:
        off = self.opt.get(KEY_EXECUTION_INFO)
        if off is None:
            return None
        media, version, base_version, title = struct.unpack_from(">IIII", self.data, off)
        return {"media_id": media, "version": version,
                "base_version": base_version, "title_id": title}

    def file_format(self) -> tuple[int, int, list[tuple[int, int]]]:
        """(encryption, compression, basic-compression blocks)."""
        b = self.opt_bytes(KEY_FILE_FORMAT_INFO)
        if b is None:
            raise XexError("no file format info header")
        size, enc, comp = struct.unpack_from(">IHH", b, 0)
        blocks = []
        if comp == COMPRESSION_BASIC:
            for o in range(8, size, 8):
                blocks.append(struct.unpack_from(">II", b, o))
        return enc, comp, blocks

    def static_libraries(self) -> list[tuple[str, int, int, int, int]]:
        """(name, major, minor, build, qfe) per library the image was linked
        with."""
        b = self.opt_bytes(KEY_STATIC_LIBRARIES)
        out = []
        if b is None:
            return out
        for o in range(4, len(b), 16):
            name = b[o:o + 8].rstrip(b"\0").decode("ascii")
            major, minor, build, tail = struct.unpack_from(">HHHH", b, o + 8)
            out.append((name, major, minor, build, tail & 0xFF))
        return out

    def import_libraries(self) -> list[ImportLibrary]:
        b = self.opt_bytes(KEY_IMPORT_LIBRARIES)
        libs: list[ImportLibrary] = []
        if b is None:
            return libs
        _size, strsize, count = struct.unpack_from(">III", b, 0)
        names = [s.decode("ascii") for s in b[12:12 + strsize].split(b"\0") if s]
        o = 12 + strsize

        def ver(x):
            return (x >> 28, (x >> 24) & 0xF, (x >> 8) & 0xFFFF, x & 0xFF)

        for _ in range(count):
            lsize, = struct.unpack_from(">I", b, o)
            _id, version, version_min, name_index, n = struct.unpack_from(
                ">IIIHH", b, o + 4 + 20)
            recs = list(struct.unpack_from(f">{n}I", b, o + 4 + 20 + 16))
            libs.append(ImportLibrary(names[name_index & 0xFF], ver(version),
                                      ver(version_min), recs))
            o += lsize
        return libs


def parse(data: bytes) -> Xex:
    if data[:4] != b"XEX2":
        raise XexError(f"not an XEX2 file (magic {data[:4]!r})")
    flags, pe_off, _res, sec_off, count = struct.unpack_from(">IIIII", data, 4)
    opt: dict[int, int] = {}
    for i in range(count):
        key, value = struct.unpack_from(">II", data, 24 + 8 * i)
        opt[key] = value
    return Xex(data, flags, pe_off, sec_off, opt)


def image(x: Xex) -> bytes:
    """The executable's image as the loader maps it at its base address:
    decrypted, with the basic-compression zero runs restored."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    enc, comp, blocks = x.file_format()
    if comp != COMPRESSION_BASIC:
        raise XexError(f"compression type {comp} is not handled (only basic, 1)")
    payload = x.data[x.pe_data_offset:]
    if enc == ENCRYPTION_NORMAL:
        d = Cipher(algorithms.AES(XEX2_RETAIL_KEY), modes.ECB()).decryptor()
        session = d.update(x.wrapped_key) + d.finalize()
        if len(payload) % 16:
            raise XexError("encrypted payload is not a whole number of AES blocks")
        d = Cipher(algorithms.AES(session), modes.CBC(bytes(16))).decryptor()
        payload = d.update(payload) + d.finalize()
    elif enc != ENCRYPTION_NONE:
        raise XexError(f"encryption type {enc} is not handled")
    out = bytearray()
    pos = 0
    for data_size, zero_size in blocks:
        out += payload[pos:pos + data_size]
        out += bytes(zero_size)
        pos += data_size
    if pos != len(payload):
        raise XexError(f"basic-compression blocks cover {pos} of {len(payload)} payload bytes")
    if len(out) != x.image_size:
        raise XexError(f"expanded image is {len(out):#x} bytes, header says {x.image_size:#x}")
    if out[:2] != b"MZ":
        raise XexError("expanded image does not start with MZ: wrong key or layout")
    return bytes(out)
