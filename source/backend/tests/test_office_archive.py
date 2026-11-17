"""Synthetic OOXML fixtures; no application startup, accounts or model access."""
import io
import struct
import unittest
import warnings
import zipfile
from functools import lru_cache
from unittest.mock import patch

from app.services.file_parsing import parse_docx
from app.services.markdown_conversion import MarkdownConversionError, convert_to_markdown


@lru_cache
def office_bytes(kind="docx"):
    stream = io.BytesIO()
    if kind == "docx":
        from docx import Document
        document = Document()
        document.add_paragraph("Synthetic ordinary document")
        document.save(stream)
    elif kind == "xlsx":
        from openpyxl import Workbook
        document = Workbook()
        document.active.append(["vendor", "product_name"])
        document.active.append(["Synthetic vendor", "Synthetic product"])
        document.save(stream)
        document.close()
    else:
        from pptx import Presentation
        document = Presentation()
        slide = document.slides.add_slide(document.slide_layouts[1])
        slide.shapes.title.text = "Synthetic ordinary presentation"
        slide.placeholders[1].text = "Synthetic slide text"
        document.save(stream)
    return stream.getvalue()


def repack(content, additions=(), replacements=None, removed=()):
    output = io.BytesIO()
    replacements = replacements or {}
    with zipfile.ZipFile(io.BytesIO(content)) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for info in original.infolist():
            if info.filename not in removed:
                target.writestr(info, replacements.get(info.filename, original.read(info)))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            for name, value in additions:
                if isinstance(name, str):
                    # ZipInfo normalizes backslashes on Windows. Preserve the
                    # hostile bytes so this is a parser test, not a writer test.
                    info = zipfile.ZipInfo("fixture")
                    info.filename = name
                    info.orig_filename = name
                    info.compress_type = zipfile.ZIP_DEFLATED
                    name = info
                target.writestr(name, value)
    return output.getvalue()


DTD = b'<!DOCTYPE x [<!ENTITY e "unsafe">]><x>&e;</x>'


class ExistingParserRejectionTests(unittest.TestCase):
    def test_docx_rejects_ignored_unsafe_xml(self):
        unsafe = repack(office_bytes(), [("unused.xml", DTD)])
        with self.assertRaises(ValueError):
            parse_docx(unsafe)

    def test_markitdown_rejects_unsafe_docx_xlsx_pptx(self):
        for kind in ("docx", "xlsx", "pptx"):
            with self.subTest(kind=kind):
                unsafe = repack(office_bytes(kind), [("unused.xml", DTD)])
                with self.assertRaises(MarkdownConversionError):
                    convert_to_markdown(unsafe, "synthetic." + kind)

    def test_renamed_unsafe_zip_cannot_reach_converter_or_text_passthrough(self):
        unsafe = repack(office_bytes(), [("unused.xml", DTD)])
        for name in ("synthetic.pdf", "synthetic.html", "synthetic.csv", "synthetic.xls", "synthetic.txt"):
            with self.subTest(name=name), self.assertRaises(MarkdownConversionError):
                convert_to_markdown(unsafe, name)

    def test_ordinary_real_converters(self):
        self.assertIn("Synthetic ordinary document", " ".join(parse_docx(office_bytes())))
        for kind, text in (("docx", "Synthetic ordinary document"), ("xlsx", "Synthetic product"), ("pptx", "Synthetic slide text")):
            with self.subTest(kind=kind):
                self.assertIn(text, convert_to_markdown(office_bytes(kind), "synthetic." + kind))


class ArchivePreflightTests(unittest.TestCase):
    def preflight(self, content, filename="synthetic.docx", **limits):
        # Keep import local so RED also exercises the existing parser regressions.
        from app.services.office_archive import OfficeLimits, preflight_office_archive
        return preflight_office_archive(content, filename, limits=OfficeLimits(**limits))

    def reject(self, content, filename="synthetic.docx", **limits):
        with self.assertRaises(ValueError):
            self.preflight(content, filename, **limits)

    def test_default_contract(self):
        from app.services.office_archive import OfficeLimits
        limits = OfficeLimits()
        self.assertEqual((limits.compressed_bytes, limits.expanded_bytes, limits.member_bytes), (25 * 1024**2, 64 * 1024**2, 16 * 1024**2))
        self.assertEqual((limits.members, limits.directory_bytes, limits.ratio, limits.path_depth), (4096, 4 * 1024**2, 200, 32))
        self.assertEqual((limits.xml_depth, limits.xml_elements, limits.seconds), (128, 200000, 5))

    def test_plain_text_is_not_a_package(self):
        self.assertIsNone(self.preflight(b"synthetic text", "ordinary.txt"))

    def test_real_packages_and_renamed_valid_package(self):
        for kind in ("docx", "xlsx", "pptx"):
            self.assertEqual(kind, self.preflight(office_bytes(kind), "ordinary." + kind))
        self.assertEqual("docx", self.preflight(office_bytes(), "renamed.pdf"))

    def test_traversal_absolute_backslash_encoded_and_deep_paths(self):
        for name in ("../evil.xml", "/evil.xml", "C:/evil.xml", "a\\evil.xml", "a/%2e%2e/evil.xml", "a/./evil.xml", "a//evil.xml", "/".join(["a"] * 33) + "/x"):
            with self.subTest(name=name):
                self.reject(repack(office_bytes(), [(name, b"<x/>")]))

    def test_duplicates_case_alias_and_symlink(self):
        for name in ("word/document.xml", "WORD/document.xml"):
            with self.subTest(name=name):
                self.reject(repack(office_bytes(), [(name, b"<x/>")]))
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (0o120777 << 16)
        self.reject(repack(office_bytes(), [(link, b"target")]))

    def test_nested_and_disguised_archives(self):
        for payload in (office_bytes("xlsx"), b"preamble" + office_bytes("xlsx"), b"PK\x03\x04broken"):
            with self.subTest(prefix=payload[:12]):
                self.reject(repack(office_bytes(), [("media/image.bin", payload)]))

    def test_xml_dtd_entities_utf16_and_nonstandard_part_names(self):
        for payload in (DTD, DTD.decode().encode("utf-16"), DTD.decode().encode("utf-16-be"), b"<!DOCTYPE x SYSTEM 'https://example.invalid/x'><x/>"):
            for name in ("extra.xml", "extra.rels", "payload.data"):
                with self.subTest(name=name, prefix=payload[:12]):
                    self.reject(repack(office_bytes(), [(name, payload)]))

    def test_content_type_xml_without_xml_suffix(self):
        with zipfile.ZipFile(io.BytesIO(office_bytes())) as archive:
            types = archive.read("[Content_Types].xml").replace(b"</Types>", b'<Override PartName="/odd.part" ContentType="application/example+xml"/></Types>')
        self.reject(repack(office_bytes(), [("odd.part", b"not valid XML")], {"[Content_Types].xml": types}))

    def test_empty_required_xml_parts_fail_with_bounded_error(self):
        from app.services.office_archive import OfficeArchiveError
        for name in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
            with self.subTest(name=name), self.assertRaises(OfficeArchiveError):
                self.preflight(repack(office_bytes(), replacements={name: b""}))

    def test_malformed_xml(self):
        self.reject(repack(office_bytes(), [("unused.xml", b"<x><broken></x>")]))

    def test_xml_depth_and_elements_are_bounded(self):
        self.reject(repack(office_bytes(), [("unused.xml", b"<x>" * 129 + b"</x>" * 129)]))
        # Low custom bound keeps fixture tiny; total XML elements are counted.
        self.reject(office_bytes("xlsx"), "test.xlsx", xml_elements=20)

    def test_missing_parts_wrong_kind_and_arbitrary_zip(self):
        for name in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
            self.reject(repack(office_bytes(), removed=(name,)))
        self.reject(office_bytes("xlsx"), "wrong.docx")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("file.txt", "arbitrary zip")
        self.reject(output.getvalue(), "renamed.pdf")
        self.reject(b"not a zip")

    def test_alternative_main_part_is_validated(self):
        content = office_bytes()
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            main = archive.read("word/document.xml")
            types = archive.read("[Content_Types].xml").replace(b"/word/document.xml", b"/alternate.data")
            rels = archive.read("_rels/.rels").replace(b"word/document.xml", b"alternate.data")
        for payload, accepted in ((main, True), (DTD.decode().encode("utf-16"), False)):
            changed = repack(content, [("alternate.data", payload)], {"[Content_Types].xml": types, "_rels/.rels": rels}, ("word/document.xml",))
            if accepted:
                self.assertEqual("docx", self.preflight(changed))
            else:
                self.reject(changed)

    def test_size_member_aggregate_ratio_and_directory_limits(self):
        content = office_bytes("xlsx")
        for overrides in ({"compressed_bytes": len(content) - 1}, {"member_bytes": 500}, {"expanded_bytes": 2000}, {"ratio": 1}, {"directory_bytes": 50}, {"members": 2}):
            with self.subTest(overrides=overrides):
                self.reject(content, "test.xlsx", **overrides)

    def test_metadata_is_checked_before_zipfile_allocation_even_if_count_lies(self):
        from app.services import office_archive
        content = bytearray(office_bytes("xlsx"))
        eocd = content.rfind(b"PK\x05\x06")
        # A forged EOCD count must not hide the real directory record count.
        struct.pack_into("<HH", content, eocd + 8, 1, 1)
        with patch.object(office_archive.zipfile, "ZipFile", side_effect=AssertionError("allocated before validation")):
            self.reject(bytes(content), "test.xlsx", members=2)

    def test_multidisk_zip64_encryption_and_unknown_compression(self):
        for offset, value, width in ((4, 1, "H"), (8, 65535, "H"), (12, 0xffffffff, "I")):
            content = bytearray(office_bytes())
            eocd = content.rfind(b"PK\x05\x06")
            struct.pack_into("<" + width, content, eocd + offset, value)
            self.reject(bytes(content))
        for offset, value in ((8, 1), (10, 99)):
            content = bytearray(office_bytes())
            central = content.find(b"PK\x01\x02")
            struct.pack_into("<H", content, central + offset, value)
            self.reject(bytes(content))

    def test_crc_and_truncation(self):
        content = bytearray(office_bytes())
        central = content.find(b"PK\x01\x02")
        struct.pack_into("<I", content, central + 16, 0)
        self.reject(bytes(content))
        self.reject(office_bytes()[:-12])

    def test_cooperative_deadline(self):
        self.reject(office_bytes(), seconds=0)


if __name__ == "__main__":
    unittest.main()
