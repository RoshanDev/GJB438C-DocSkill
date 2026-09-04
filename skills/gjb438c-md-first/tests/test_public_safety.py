from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

FORBIDDEN = (
    "".join(chr(value) for value in (0x56FD, 0x6052)),
    "".join(
        chr(value)
        for value in (
            0x6210, 0x90FD, 0x56FD, 0x6052, 0x7A7A, 0x95F4, 0x6280, 0x672F,
            0x5DE5, 0x7A0B, 0x80A1, 0x4EFD, 0x6709, 0x9650, 0x516C, 0x53F8,
        )
    ),
    "".join(chr(value) for value in (0x67, 0x75, 0x6F, 0x68, 0x65, 0x6E, 0x67)),
)
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "build", "dist"}
XML_SUFFIXES = (".xml", ".rels")


def _encoded_tokens() -> tuple[bytes, ...]:
    values: list[bytes] = []
    for token in FORBIDDEN:
        for encoding in ("utf-8", "utf-16-le", "utf-16-be"):
            values.append(token.encode(encoding))
    return tuple(values)


def _assert_payload_is_anonymized(payload: bytes, label: object) -> None:
    assert not any(token in payload for token in _encoded_tokens()), label


def test_public_repository_contains_no_organization_identity() -> None:
    repository = Path(__file__).resolve().parents[3]
    for path in repository.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repository)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        lowered = relative.as_posix().lower()
        assert not any(token.lower() in lowered for token in FORBIDDEN), relative
        _assert_payload_is_anonymized(path.read_bytes(), relative)
        if path.suffix.lower() != ".docx":
            continue
        try:
            with ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.endswith(XML_SUFFIXES):
                        _assert_payload_is_anonymized(
                            archive.read(name), f"{relative}!/{name}"
                        )
        except BadZipFile as exc:
            raise AssertionError(f"损坏的 DOCX：{relative}") from exc


def test_front_matter_master_is_anonymized_and_minimal() -> None:
    root = Path(__file__).resolve().parents[1]
    master = root / "templates/front-matter/standard-front-matter.docx"
    with ZipFile(master) as archive:
        names = set(archive.namelist())
        assert not any(name.startswith("word/media/") for name in names)
        assert not any(name.startswith("customXml/") for name in names)
        payload = b"\n".join(
            archive.read(name) for name in names if name.endswith(XML_SUFFIXES)
        )
    _assert_payload_is_anonymized(payload, master)
    text = payload.decode("utf-8", errors="ignore")
    assert "编制单位" in text
