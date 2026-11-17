"""Bounded OOXML admission checks, not a CPU/RAM or converter sandbox.

Only ordinary single-disk, non-ZIP64, unencrypted stored/deflated packages
are admitted. All members are read to EOF (including CRC validation) before
any downstream parser sees the bytes. The deadline is cooperative.
"""

import io
import itertools
import os
import stat
import struct
import time
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from xml.parsers import expat


class OfficeArchiveError(ValueError):
    """Safe, bounded error suitable for an HTTP 400 response."""


@dataclass(frozen=True)
class OfficeLimits:
    compressed_bytes: int = 25 * 1024 * 1024
    expanded_bytes: int = 64 * 1024 * 1024
    member_bytes: int = 16 * 1024 * 1024
    members: int = 4096
    directory_bytes: int = 4 * 1024 * 1024
    ratio: int = 200
    path_depth: int = 32
    xml_depth: int = 128
    xml_elements: int = 200_000
    seconds: float = 5.0


_DEFAULT_LIMITS = OfficeLimits()
_OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}
_MAIN_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml": "pptx",
}
_TYPE_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_OFFICE_RELS = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
}
_MAIN_ROOTS = {
    "docx": {"http://schemas.openxmlformats.org/wordprocessingml/2006/main|document", "http://purl.oclc.org/ooxml/wordprocessingml/main|document"},
    "xlsx": {"http://schemas.openxmlformats.org/spreadsheetml/2006/main|workbook", "http://purl.oclc.org/ooxml/spreadsheetml/main|workbook"},
    "pptx": {"http://schemas.openxmlformats.org/presentationml/2006/main|presentation", "http://purl.oclc.org/ooxml/presentationml/main|presentation"},
}
_CHUNK = 64 * 1024


def _reject(reason):
    raise OfficeArchiveError("Office file rejected: " + reason)


def _check_time(deadline):
    if time.monotonic() >= deadline:
        _reject("preflight time limit exceeded")


def _safe_path(name, limits, *, directory=False):
    # Refuse aliases rather than guessing how each downstream parser resolves
    # URI escaping, Windows paths, Unicode or case differences.
    parts = name.rstrip("/").split("/") if directory else name.split("/")
    if (not name or name.startswith("/") or "\\" in name or ":" in name
            or "%" in name or any(ord(ch) < 32 or ord(ch) == 127 for ch in name)
            or any(part in ("", ".", "..") or part.endswith((".", " ")) for part in parts)
            or len(parts) > limits.path_depth):
        _reject("unsafe member path")
    return unicodedata.normalize("NFC", name).casefold()


def _check_extra(content, start, length):
    end = start + length
    while start < end:
        if start + 4 > end:
            _reject("invalid ZIP extra field")
        tag, size = struct.unpack_from("<HH", content, start)
        if tag == 1:
            _reject("ZIP64 packages are unsupported")
        start += 4 + size
        if start > end:
            _reject("invalid ZIP extra field")


def _directory_preflight(content, limits, deadline):
    """Walk raw central records BEFORE ZipFile builds its ZipInfo list.

    EOCD counts are untrusted: count actual records and check local headers,
    declared allocations and overlapping ranges before constructing ZipFile.
    """
    if len(content) > limits.compressed_bytes:
        _reject("compressed size limit exceeded")
    end = content.rfind(b"PK\x05\x06", max(0, len(content) - 65557))
    if end < 0 or end + 22 > len(content):
        _reject("invalid ZIP directory")
    disk, directory_disk, disk_count, count, size, offset, comment = struct.unpack_from("<4H2IH", content, end + 4)
    if (count == 0xffff or disk_count == 0xffff or size == 0xffffffff or offset == 0xffffffff
            or content[max(0, end - 20):end].startswith(b"PK\x06\x07")):
        _reject("ZIP64 packages are unsupported")
    if disk or directory_disk or disk_count != count:
        _reject("multi-disk packages are unsupported")
    if count > limits.members or size > limits.directory_bytes:
        _reject("ZIP directory limit exceeded")
    if end + 22 + comment != len(content) or offset + size != end or not content.startswith(b"PK\x03\x04"):
        _reject("invalid ZIP directory layout")

    cursor, actual, expanded, compressed = offset, 0, 0, 0
    names, ranges = set(), []
    while cursor < end:
        _check_time(deadline)
        actual += 1
        if actual > limits.members:
            _reject("member count limit exceeded")
        if cursor + 46 > end or content[cursor:cursor + 4] != b"PK\x01\x02":
            _reject("invalid central directory record")
        flags, method = struct.unpack_from("<HH", content, cursor + 8)
        packed, unpacked = struct.unpack_from("<II", content, cursor + 20)
        name_len, extra_len, comment_len, member_disk = struct.unpack_from("<4H", content, cursor + 28)
        attributes, local = struct.unpack_from("<II", content, cursor + 38)
        record_end = cursor + 46 + name_len + extra_len + comment_len
        if record_end > end:
            _reject("invalid directory record size")
        if member_disk:
            _reject("multi-disk packages are unsupported")
        if packed == 0xffffffff or unpacked == 0xffffffff or local == 0xffffffff:
            _reject("ZIP64 packages are unsupported")
        if flags & (1 | 0x20 | 0x40 | 0x2000):
            _reject("encrypted or patched packages are unsupported")
        if method not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            _reject("unsupported ZIP compression")
        if stat.S_IFMT(attributes >> 16) not in (0, stat.S_IFREG, stat.S_IFDIR):
            _reject("special files and symlinks are unsupported")
        raw_name = content[cursor + 46:cursor + 46 + name_len]
        name = raw_name.decode("utf-8" if flags & 0x800 else "cp437")
        key = _safe_path(name, limits, directory=name.endswith("/"))
        if key in names:
            _reject("duplicate or aliased member")
        names.add(key)
        _check_extra(content, cursor + 46 + name_len, extra_len)
        expanded += unpacked
        compressed += packed
        if (unpacked > limits.member_bytes or expanded > limits.expanded_bytes
                or unpacked > max(1, packed) * limits.ratio):
            _reject("expanded size or compression ratio limit exceeded")
        if local + 30 > offset or content[local:local + 4] != b"PK\x03\x04":
            _reject("invalid local header")
        local_flags, local_method = struct.unpack_from("<HH", content, local + 6)
        local_name, local_extra = struct.unpack_from("<HH", content, local + 26)
        data_start = local + 30 + local_name + local_extra
        if (data_start + packed > offset or local_flags != flags or local_method != method
                or content[local + 30:local + 30 + local_name] != raw_name):
            _reject("inconsistent local header")
        _check_extra(content, local + 30 + local_name, local_extra)
        local_packed, local_unpacked = struct.unpack_from("<II", content, local + 18)
        if local_packed == 0xffffffff or local_unpacked == 0xffffffff:
            _reject("ZIP64 packages are unsupported")
        if not flags & 8 and (local_packed != packed or local_unpacked != unpacked):
            _reject("inconsistent ZIP member sizes")
        ranges.append((local, data_start + packed))
        cursor = record_end
    if cursor != end or actual != count or not actual:
        _reject("inconsistent directory count")
    if expanded > max(1, compressed) * limits.ratio:
        _reject("package compression ratio limit exceeded")
    previous = 0
    for start, stop in sorted(ranges):
        if start < previous:
            _reject("overlapping ZIP members")
        previous = stop


class _XMLCheck:
    """Expat callbacks reject declarations before entity expansion, in any encoding."""

    def __init__(self, limits, deadline, element_budget, *, collect=False):
        self.parser = expat.ParserCreate(namespace_separator="|")
        self.depth = 0
        self.root = None
        self.records = []

        def forbidden(*args):
            _reject("XML DTD and entity declarations are unsupported")

        def start(name, attrs):
            _check_time(deadline)
            self.depth += 1
            element_budget[0] += 1
            if self.depth > limits.xml_depth or element_budget[0] > limits.xml_elements:
                _reject("XML complexity limit exceeded")
            if self.root is None:
                self.root = name
            if collect:
                self.records.append((name, attrs))

        def finish(name):
            self.depth -= 1

        self.parser.StartElementHandler = start
        self.parser.EndElementHandler = finish
        self.parser.StartDoctypeDeclHandler = forbidden
        self.parser.EntityDeclHandler = forbidden
        self.parser.ExternalEntityRefHandler = forbidden
        self.parser.SkippedEntityHandler = forbidden


def _looks_xml(chunk):
    # Detection only; Expat receives the original bytes and validates encoding.
    return chunk[:1024].replace(b"\x00", b"").lstrip(b"\xef\xbb\xbf\xff\xfe \t\r\n").startswith(b"<")


def _member_chunks(content, info, limits, deadline):
    """Read raw members without trusting ZipExtFile's declared-size truncation.

    The directory/local-header layout has already been validated. Each zlib
    call has a bounded output allocation, and only a complete single stream
    whose actual expanded size and CRC match the directory is admitted.
    """
    name_length, extra_length = struct.unpack_from("<HH", content, info.header_offset + 26)
    cursor = info.header_offset + 30 + name_length + extra_length
    end = cursor + info.compress_size
    decoder = zlib.decompressobj(-zlib.MAX_WBITS) if info.compress_type == zipfile.ZIP_DEFLATED else None
    pending = b""
    total, checksum = 0, 0
    while cursor < end or pending or (decoder is not None and not decoder.eof):
        _check_time(deadline)
        if not pending:
            pending = content[cursor:min(end, cursor + _CHUNK)]
            cursor += len(pending)
        if decoder is None:
            chunk, pending = pending, b""
        else:
            input_length = len(pending)
            maximum = min(_CHUNK, info.file_size - total + 1, limits.member_bytes - total + 1)
            chunk = decoder.decompress(pending, maximum)
            pending = decoder.unconsumed_tail
            if decoder.unused_data or (decoder.eof and (pending or cursor != end)):
                _reject("trailing data after DEFLATE stream")
            if not chunk and not decoder.eof:
                if (not pending and cursor == end) or (pending and len(pending) >= input_length):
                    _reject("incomplete DEFLATE stream")
        total += len(chunk)
        if total > info.file_size or total > limits.member_bytes:
            _reject("member read limit exceeded")
        checksum = zlib.crc32(chunk, checksum)
        if chunk:
            yield chunk
    if decoder is not None and not decoder.eof:
        _reject("incomplete DEFLATE stream")
    if total != info.file_size:
        _reject("inconsistent expanded member size")
    if checksum != info.CRC:
        _reject("invalid member CRC")


def _read_member(content, info, limits, deadline, element_budget, *, xml=False, collect=False):
    checker = None
    total = 0
    tail = b""
    chunks = iter(_member_chunks(content, info, limits, deadline))
    # One compressed input chunk may yield only one plaintext byte. Preserve
    # the original 1-KiB content-sniffing window across such yields, including
    # split Unicode BOMs and ZIP signatures. Buffer at most _CHUNK + 1023 bytes.
    prefix = bytearray()
    for chunk in chunks:
        prefix.extend(chunk)
        if len(prefix) >= 1024:
            break
    for chunk in itertools.chain((bytes(prefix),) if prefix else (), chunks):
        if total == 0:
            if chunk.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
                _reject("nested packages are unsupported")
            if xml or _looks_xml(chunk):
                checker = _XMLCheck(limits, deadline, element_budget, collect=collect)
        total += len(chunk)
        tail = (tail + chunk)[-65557:]
        if checker:
            checker.parser.Parse(chunk, False)
    # Also catch ZIPs hidden behind a non-ZIP prefix or renamed binary part.
    if b"PK\x05\x06" in tail:
        _reject("nested or disguised packages are unsupported")
    if checker:
        checker.parser.Parse(b"", True)
    return checker


def _validate_package(archive, content, limits, deadline):
    infos = {info.filename: info for info in archive.infolist()}
    if "[Content_Types].xml" not in infos or "_rels/.rels" not in infos:
        _reject("required OOXML package parts are missing")
    budget = [0]
    types = _read_member(content, infos["[Content_Types].xml"], limits, deadline, budget, xml=True, collect=True)
    if types is None or types.root != _TYPE_NS + "|Types":
        _reject("invalid OOXML content types")
    defaults, overrides = {}, {}
    for tag, attrs in types.records[1:]:
        if tag == _TYPE_NS + "|Override":
            part = attrs.get("PartName", "")
            if not part.startswith("/"):
                _reject("invalid content type part")
            _safe_path(part[1:], limits)
            if part[1:] in overrides or part[1:] not in infos:
                _reject("invalid or duplicate content type part")
            overrides[part[1:]] = attrs.get("ContentType", "")
        elif tag == _TYPE_NS + "|Default":
            extension = attrs.get("Extension", "").lower()
            if not extension or extension in defaults:
                _reject("invalid or duplicate default content type")
            defaults[extension] = attrs.get("ContentType", "")
        else:
            _reject("invalid content type record")
    rels = _read_member(content, infos["_rels/.rels"], limits, deadline, budget, xml=True, collect=True)
    if rels is None or rels.root != _REL_NS + "|Relationships":
        _reject("invalid package relationships")
    main_parts = []
    for tag, attrs in rels.records[1:]:
        if tag == _REL_NS + "|Relationship" and attrs.get("Type") in _OFFICE_RELS:
            if attrs.get("TargetMode", "Internal") != "Internal":
                _reject("external main part is unsupported")
            target = attrs.get("Target", "").removeprefix("/")
            _safe_path(target, limits)
            main_parts.append(target)
    if len(main_parts) != 1 or main_parts[0] not in infos:
        _reject("required Office document part is missing")
    main = main_parts[0]
    kind = _MAIN_TYPES.get(overrides.get(main, defaults.get(main.rsplit(".", 1)[-1].lower(), "")))
    if not kind:
        _reject("unsupported Office document content type")
    for name, info in infos.items():
        if name in ("[Content_Types].xml", "_rels/.rels"):
            continue
        mime = overrides.get(name, defaults.get(name.rsplit(".", 1)[-1].lower(), "")).lower()
        xml = name.lower().endswith((".xml", ".rels")) or mime.endswith(("/xml", "+xml")) or name == main
        checker = _read_member(content, info, limits, deadline, budget, xml=xml)
        if name == main and (checker is None or checker.root not in _MAIN_ROOTS[kind]):
            _reject("invalid Office main XML part")
    return kind


def preflight_office_archive(content: bytes, filename: str, *, limits: OfficeLimits = _DEFAULT_LIMITS) -> str | None:
    """Validate Office or ZIP-looking bytes regardless of the supplied suffix.

    Return docx/xlsx/pptx, or None for non-Office non-ZIP input. Arbitrary ZIPs
    are refused, including ZIPs renamed to rich formats that MarkItDown sniffs.
    Downstream conversions still need separate worker/resource protection.
    """
    extension = os.path.splitext(filename or "")[1].lower()
    looks_zip = content.startswith(b"PK") or b"PK\x05\x06" in content[-65557:]
    if extension not in _OFFICE_EXTENSIONS and not looks_zip:
        return None
    deadline = time.monotonic() + limits.seconds
    try:
        _check_time(deadline)
        _directory_preflight(content, limits, deadline)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            kind = _validate_package(archive, content, limits, deadline)
        if extension in _OFFICE_EXTENSIONS and extension != "." + kind:
            _reject("Office filename does not match package type")
        _check_time(deadline)
        return kind
    except OfficeArchiveError:
        raise
    except (zipfile.BadZipFile, UnicodeError, struct.error, expat.ExpatError, EOFError, OSError, RuntimeError, NotImplementedError, zlib.error) as error:
        raise OfficeArchiveError("Office file rejected: malformed or unsupported package") from error
