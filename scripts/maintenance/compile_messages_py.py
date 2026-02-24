"""Minimal pure-Python .po -> .mo compiler (fallback when msgfmt isn't available).

Usage (PowerShell):
  & ./.venv/Scripts/python.exe compile_messages_py.py -l ar

This will look for locale/<lang>/LC_MESSAGES/django.po and produce django.mo.

Limitations: Handles msgid, msgid_plural, msgstr, msgstr[n] with continued
string literals. Comments/#, fuzzy flags ignored. Enough for our project.
"""
from __future__ import annotations
import argparse
import os
import re
import struct
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple

PO_ENTRY_RE = re.compile(r'^(msgid|msgid_plural|msgstr(?:\[\d+\])?)\s+"(.*)"\s*$')

def unescape(s: str) -> str:
    return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\'', "'")

def parse_po(po_text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    msgid = None
    msgid_plural = None
    msgstrs: dict[int, str] = {}
    collecting = None  # 'msgid' / 'msgid_plural' / 'msgstr[n]'

    def flush():
        nonlocal msgid, msgid_plural, msgstrs
        if msgid is not None:
            if msgid_plural is not None:
                # build original key with NUL separator per GNU gettext
                orig = f"{msgid}\x00{msgid_plural}"
                # translations joined by NUL
                max_index = max(msgstrs) if msgstrs else -1
                trans_parts = [msgstrs.get(i, '') for i in range(max_index+1)]
                trans = "\x00".join(trans_parts)
                entries.append((orig, trans))
            else:
                trans = msgstrs.get(0, '')
                entries.append((msgid, trans))
        msgid = None
        msgid_plural = None
        msgstrs = {}

    for raw_line in po_text.splitlines():
        line = raw_line.strip('\n')
        if not line or line.startswith('#'):
            continue
        m = PO_ENTRY_RE.match(line)
        if m:
            key, first = m.group(1), m.group(2)
            if key == 'msgid':
                flush()
                msgid = unescape(first)
                collecting = 'msgid'
            elif key == 'msgid_plural':
                msgid_plural = unescape(first)
                collecting = 'msgid_plural'
            elif key.startswith('msgstr'):
                if key == 'msgstr':
                    idx = 0
                else:
                    idx = int(key[key.index('[')+1:key.index(']')])
                msgstrs[idx] = unescape(first)
                collecting = f'msgstr[{idx}]'
            continue
        # continued string literal?
        if line.startswith('"') and line.endswith('"') and collecting:
            text = unescape(line[1:-1])
            if collecting == 'msgid':
                msgid = (msgid or '') + text
            elif collecting == 'msgid_plural':
                msgid_plural = (msgid_plural or '') + text
            elif collecting.startswith('msgstr['):
                idx = int(collecting[7:-1])
                msgstrs[idx] = msgstrs.get(idx, '') + text
            elif collecting == 'msgstr':
                msgstrs[0] = msgstrs.get(0, '') + text
            continue
        # otherwise ignore
    flush()
    return entries

def write_mo(entries: Sequence[tuple[str, str]], mo_path: Path) -> None:
    # Ensure header (msgid "") is first; if missing create one.
    header_entry = None
    others = []
    for k, v in entries:
        if k == '':
            header_entry = (k, v)
        else:
            others.append((k, v))
    if header_entry is None:
        header_entry = ('', 'Content-Type: text/plain; charset=UTF-8\n')
    # Sort others by msgid to maintain deterministic order.
    others.sort(key=lambda kv: kv[0])
    ordered = [header_entry] + others

    # Build binary .mo (GNU gettext little endian)
    # Reference: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html
    magic = 0x950412de
    version = 0
    n = len(ordered)
    # header size: 7 * 4 bytes (we set hash table size/offset to 0)
    orig_tab_offset = 28
    # Each table has n entries * 8 bytes
    trans_tab_offset = orig_tab_offset + n * 8
    # String data starts after both tables
    string_offset = trans_tab_offset + n * 8

    originals = []
    translations = []
    orig_table = []
    trans_table = []
    off = string_offset
    for orig, trans in ordered:
        orig_bytes = orig.encode('utf-8')
        trans_bytes = trans.encode('utf-8')
        originals.append(orig_bytes + b'\x00')
        translations.append(trans_bytes + b'\x00')
        orig_table.append((len(orig_bytes), off))
        off += len(orig_bytes) + 1
    for trans_bytes, (orig_len, orig_off) in zip(translations, orig_table):
        trans_table.append((len(trans_bytes)-1, off))
        off += len(trans_bytes)

    with open(mo_path, 'wb') as f:
        f.write(struct.pack('<Iiiiiii', magic, version, n, orig_tab_offset, trans_tab_offset, 0, 0))
        for length, offset in orig_table:
            f.write(struct.pack('<II', length, offset))
        for length, offset in trans_table:
            f.write(struct.pack('<II', length, offset))
        for data in originals:
            f.write(data)
        for data in translations:
            f.write(data)

def compile_locale(lang: str, base_dir: Path) -> None:
    """Compile a single locale .po into .mo and perform a quick validity check.

    The validity check attempts to load the produced file with gettext to catch
    table ordering / offset issues early (these manifest as UnicodeDecodeError
    in Django views like the reported dashboard error).
    """
    po_path = base_dir / 'locale' / lang / 'LC_MESSAGES' / 'django.po'
    mo_path = po_path.with_suffix('.mo')
    if not po_path.exists():
        raise SystemExit(f"PO file not found: {po_path}")
    text = po_path.read_text(encoding='utf-8')
    entries = parse_po(text)
    write_mo(entries, mo_path)
    # Quick sanity load
    try:
        import gettext
        with open(mo_path, 'rb') as fh:
            gettext.GNUTranslations(fh)
    except Exception as e:  # pragma: no cover - diagnostic path
        raise SystemExit(f"ERROR: Compiled mo failed to load ({lang}): {e}")
    print(f"تم تحويل {po_path} -> {mo_path} بعدد {len(entries)} مدخلات")

def iter_languages(base_dir: Path) -> Iterator[str]:
    loc_dir = base_dir / 'locale'
    if not loc_dir.exists():
        return
    for lang_dir in loc_dir.iterdir():
        po_file = lang_dir / 'LC_MESSAGES' / 'django.po'
        if po_file.exists():
            yield lang_dir.name


def main():
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('-l', '--language', help='Locale language code, e.g. ar')
    g.add_argument('-a', '--all', action='store_true', help='Compile all locale/* languages')
    parser.add_argument('--clean', action='store_true', help='Delete existing .mo before compiling')
    args = parser.parse_args()
    base = Path(__file__).parent
    if args.all:
        langs = list(iter_languages(base))
        if not langs:
            raise SystemExit('No locales found under locale/*')
    else:
        langs = [args.language]
    for lang in langs:
        if args.clean:
            mo_path = base / 'locale' / lang / 'LC_MESSAGES' / 'django.mo'
            if mo_path.exists():
                try:
                    mo_path.unlink()
                    print(f"Removed old {mo_path}")
                except OSError as e:
                    print(f"Could not remove {mo_path}: {e}")
        compile_locale(lang, base)

if __name__ == '__main__':
    main()
