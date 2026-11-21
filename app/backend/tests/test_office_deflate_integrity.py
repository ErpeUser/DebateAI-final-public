"""Tiny malformed DEFLATE members must not hide behind correct ZIP metadata."""

import io
import struct
import unittest
import zipfile
import zlib
from types import SimpleNamespace
from unittest.mock import patch

from app.services.markdown_conversion import (
    MarkdownConversionError,
    convert_to_markdown,
)
from app.services.office_archive import OfficeArchiveError, preflight_office_archive

from tests.test_office_archive import DTD, office_bytes


def stored_block(data, *, final=True):
    assert len(data) < 65536
    return (
        bytes([int(final)]) + struct.pack("<HH", len(data), len(data) ^ 0xFFFF) + data
    )


def package_with_raw_member(packed, declared=b"Synthetic plain payload", *, method=8):
    """Rebuild ordinary fixture bytes; change only one ignored member's stream.

    No files are extracted. Offsets, sizes and CRC agree with declared plaintext,
    so a rejection proves raw-stream integrity rather than unrelated ZIP damage.
    """
    with zipfile.ZipFile(io.BytesIO(office_bytes())) as original:
        entries = [
            (entry.filename, original.read(entry)) for entry in original.infolist()
        ]
    entries.append(("synthetic-stream.bin", declared))
    local, directory = bytearray(), bytearray()
    for name, content in entries:
        compressor = zlib.compressobj(wbits=-15)
        compressed = (
            packed
            if name == "synthetic-stream.bin"
            else compressor.compress(content) + compressor.flush()
        )
        current_method = method if name == "synthetic-stream.bin" else 8
        encoded = name.encode("utf-8")
        crc = zlib.crc32(content)
        offset = len(local)
        local.extend(
            struct.pack(
                "<4s5H3I2H",
                b"PK\x03\x04",
                20,
                0x800,
                current_method,
                0,
                33,
                crc,
                len(compressed),
                len(content),
                len(encoded),
                0,
            )
        )
        local.extend(encoded)
        local.extend(compressed)
        directory.extend(
            struct.pack(
                "<4s6H3I5H2I",
                b"PK\x01\x02",
                20,
                20,
                0x800,
                current_method,
                0,
                33,
                crc,
                len(compressed),
                len(content),
                len(encoded),
                0,
                0,
                0,
                0,
                0,
                offset,
            )
        )
        directory.extend(encoded)
    end = struct.pack(
        "<4s4H2IH",
        b"PK\x05\x06",
        0,
        0,
        len(entries),
        len(entries),
        len(directory),
        len(local),
        0,
    )
    return bytes(local + directory + end)


class OfficeDeflateIntegrityTests(unittest.TestCase):
    payload = b"Synthetic plain payload"

    def reject(self, packed, declared=None):
        body = package_with_raw_member(
            packed, self.payload if declared is None else declared
        )
        with self.assertRaises(OfficeArchiveError):
            preflight_office_archive(body, "synthetic.docx")

    def test_rejects_nonterminal_stream_despite_matching_plaintext_and_crc(self):
        self.reject(stored_block(self.payload, final=False))

    def test_rejects_nonterminal_empty_member(self):
        self.reject(stored_block(b"", final=False), b"")

    def test_rejects_trailing_bytes_after_the_stream_end(self):
        self.reject(stored_block(self.payload) + b"not part of this stream")

    def test_rejects_concatenated_raw_deflate_streams(self):
        self.reject(stored_block(self.payload) + stored_block(b"additional stream"))

    def test_rejects_hidden_expanded_tail_beyond_declared_size(self):
        self.reject(stored_block(self.payload + b"undeclared bytes"))

    def test_rejects_expansion_with_zero_declared_size(self):
        self.reject(stored_block(b"undeclared bytes"), b"")

    def test_accepts_exact_complete_and_empty_members(self):
        for value in (self.payload, b""):
            with self.subTest(size=len(value)):
                self.assertEqual(
                    "docx",
                    preflight_office_archive(
                        package_with_raw_member(stored_block(value), value),
                        "synthetic.docx",
                    ),
                )

    def test_accepts_multi_block_stream_and_small_read_chunks(self):
        raw = stored_block(self.payload[:7], final=False) + stored_block(
            self.payload[7:]
        )
        with patch("app.services.office_archive._CHUNK", 1024):
            self.assertEqual(
                "docx",
                preflight_office_archive(
                    package_with_raw_member(raw, self.payload), "synthetic.docx"
                ),
            )

    def test_stored_member_cannot_hide_bytes_beyond_the_claimed_size(self):
        content = package_with_raw_member(
            self.payload + b"undeclared bytes", self.payload, method=0
        )
        with self.assertRaises(OfficeArchiveError):
            preflight_office_archive(content, "synthetic.docx")

    def test_ordinary_stored_member_still_passes(self):
        self.assertEqual(
            "docx",
            preflight_office_archive(
                package_with_raw_member(self.payload, self.payload, method=0),
                "synthetic.docx",
            ),
        )

    def test_deflate_allocations_are_bounded_per_call(self):
        from app.services import office_archive

        constructor = zlib.decompressobj
        observed = []

        class BoundedSpy:
            def __init__(self, *args, **kwargs):
                self.inner = constructor(*args, **kwargs)

            def __getattr__(self, name):
                return getattr(self.inner, name)

            def decompress(self, data, max_length=0):
                observed.append(max_length)
                if not 0 < max_length <= 65536:
                    raise AssertionError("Unbounded decompression output request")
                return self.inner.decompress(data, max_length)

        content = package_with_raw_member(stored_block(self.payload))
        with patch.object(office_archive.zlib, "decompressobj", BoundedSpy):
            self.assertEqual(
                "docx", preflight_office_archive(content, "synthetic.docx")
            )
        self.assertTrue(observed)

    def test_large_member_spans_bounded_input_and_output_chunks(self):
        import random

        payload = random.Random(917).randbytes(200000)
        compressor = zlib.compressobj(wbits=-15)
        packed = compressor.compress(payload) + compressor.flush()
        with patch("app.services.office_archive._CHUNK", 2048):
            self.assertEqual(
                "docx",
                preflight_office_archive(
                    package_with_raw_member(packed, payload), "synthetic.docx"
                ),
            )

    def test_data_descriptor_packages_remain_valid(self):
        class Unseekable(io.BytesIO):
            def seek(self, *_args):
                raise OSError("Synthetic unseekable writer")

        output = Unseekable()
        with zipfile.ZipFile(io.BytesIO(office_bytes())) as original:
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                for info in original.infolist():
                    archive.writestr(info.filename, original.read(info))
        self.assertEqual(
            "docx", preflight_office_archive(output.getvalue(), "synthetic.docx")
        )

    def test_patched_data_flag_stays_rejected_without_zipextfile(self):
        content = bytearray(package_with_raw_member(stored_block(self.payload)))
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            info = archive.getinfo("synthetic-stream.bin")
            flags = info.flag_bits | 0x20
            struct.pack_into("<H", content, info.header_offset + 6, flags)
        cursor = content.find(b"PK\x01\x02")
        while content[cursor : cursor + 4] == b"PK\x01\x02":
            names, extras, comments = struct.unpack_from("<HHH", content, cursor + 28)
            name = content[cursor + 46 : cursor + 46 + names]
            if name == b"synthetic-stream.bin":
                struct.pack_into("<H", content, cursor + 8, flags)
                break
            cursor += 46 + names + extras + comments
        else:
            self.fail("Synthetic directory missing target")
        with self.assertRaises(OfficeArchiveError):
            preflight_office_archive(bytes(content), "synthetic.docx")

    def test_http_document_route_rejects_nonterminal_stream_before_writes(self):
        from app.routers import documents

        from tests.test_office_import_rejection import OfficeHTTPRejectionTests

        harness = OfficeHTTPRejectionTests()
        content = package_with_raw_member(stored_block(self.payload, final=False))
        harness.check_route(
            documents.upload_document, content, "synthetic.docx", local=True
        )

    def assert_split_prefix_rejected(self, first, remaining):
        # The first compressed input chunk expands to a single byte, not enough
        # for type sniffing. Metadata, size and CRC remain entirely consistent.
        raw = (
            stored_block(b"", final=False) * 13105
            + stored_block(first, final=False)
            + stored_block(remaining)
        )
        with self.assertRaises(OfficeArchiveError):
            preflight_office_archive(
                package_with_raw_member(raw, first + remaining), "synthetic.docx"
            )

    def test_xml_sniffing_spans_short_decompressed_chunks(self):
        self.assert_split_prefix_rejected(b" ", DTD)

    def test_xml_sniffing_spans_a_split_utf16_bom(self):
        xml = DTD.decode().encode("utf-16")
        self.assert_split_prefix_rejected(xml[:1], xml[1:])

    def test_nested_package_sniffing_spans_short_decompressed_chunks(self):
        self.assert_split_prefix_rejected(b"P", b"K\x03\x04synthetic")

    def test_malformed_stream_cannot_reach_the_rich_converter(self):
        content = package_with_raw_member(stored_block(self.payload, final=False))
        converter = SimpleNamespace(
            convert_stream=lambda *a, **k: SimpleNamespace(markdown="Synthetic")
        )
        with patch("markitdown.MarkItDown", return_value=converter) as factory:
            with self.assertRaises(MarkdownConversionError):
                convert_to_markdown(content, "synthetic.docx")
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
