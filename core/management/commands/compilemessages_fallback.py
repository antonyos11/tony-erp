"""Fallback compilemessages implementation (pure Python) to build .mo files
without external GNU gettext utilities. Supports basic msgid/msgstr and plural
forms aggregated with NUL separators. Does not support contexts (msgctxt).
"""

import struct
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from typing import List
from django.conf import settings

MAGIC = 0x950412de


class POEntry:
    __slots__ = ("msgid", "msgid_plural", "msgstr", "msgstr_plural")

    def __init__(self):
        self.msgid = ""
        self.msgid_plural = None
        self.msgstr = ""
        self.msgstr_plural = {}


class Command(BaseCommand):
    help = "Compile locale/*/LC_MESSAGES/django.po into django.mo (fallback)."

    def add_arguments(self, parser):
        parser.add_argument('-l', '--locale', action='append', dest='locales', help='Only compile specified locale code(s).')
        parser.add_argument('--dry-run', action='store_true', help='Parse only; do not write output files.')

    def handle(self, *args, **opts):
        locale_paths = getattr(settings, 'LOCALE_PATHS', ())
        if not locale_paths:
            raise CommandError('LOCALE_PATHS not configured.')
        wanted = opts.get('locales')
        po_files = []
        for base in locale_paths:
            base_path = Path(base)
            for po in base_path.glob('*/LC_MESSAGES/django.po'):
                code = po.parent.parent.name
                if wanted and code not in wanted:
                    continue
                po_files.append(po)
        if not po_files:
            self.stdout.write(self.style.WARNING('No .po files found.'))
            return
        for po in po_files:
            try:
                entries = self._parse_po(po)
                if opts['dry_run']:
                    self.stdout.write(f"[DRY] {po} entries={len(entries)}")
                else:
                    self._write_mo(po.with_suffix('.mo'), entries)
                    self.stdout.write(self.style.SUCCESS(f"Compiled {po} ({len(entries)})"))
            except Exception as exc:  # noqa
                raise CommandError(f"Failed {po}: {exc}")

    # --- Parsing helpers ---
    def _parse_po(self, po_path: Path):
        entries: List[POEntry] = []
        current = None
        parsing_id = False
        parsing_str = False

        def finalize():
            nonlocal current
            if current:
                if current.msgid == '' or current.msgstr or current.msgstr_plural:
                    entries.append(current)
            current = None

        with po_path.open('r', encoding='utf-8') as fh:
            for raw in fh:
                line = raw.rstrip('\n')
                if not line.strip() or line.startswith('#'):
                    continue
                if line.startswith('msgid '):
                    finalize()
                    current = POEntry()
                    current.msgid = self._unquote(line[6:].strip())
                    parsing_id = True
                    parsing_str = False
                elif line.startswith('msgid_plural') and current:
                    current.msgid_plural = self._unquote(line.split(' ', 1)[1].strip())
                elif line.startswith('msgstr[') and current:
                    idx = int(line.split(']', 1)[0].split('[')[1])
                    txt = self._unquote(line.split(']', 1)[1].strip())
                    current.msgstr_plural[idx] = txt
                    parsing_id = False
                    parsing_str = True
                elif line.startswith('msgstr') and current:
                    current.msgstr = self._unquote(line.split(' ', 1)[1].strip())
                    parsing_id = False
                    parsing_str = True
                elif line.startswith('"') and current:
                    frag = self._unquote(line.strip())
                    if parsing_id and not current.msgstr and not current.msgstr_plural:
                        current.msgid += frag
                    else:
                        if current.msgstr_plural:
                            last = max(current.msgstr_plural.keys())
                            current.msgstr_plural[last] += frag
                        elif current.msgstr:
                            current.msgstr += frag
                # ignore other tokens
        finalize()
        return entries

    # --- Writing helpers ---
    def _write_mo(self, mo_path: Path, entries: List[POEntry]):
        catalog = {}
        for e in entries:
            if e.msgid_plural and e.msgstr_plural:
                joined = '\x00'.join(e.msgstr_plural[i] for i in sorted(e.msgstr_plural.keys()))
                catalog[e.msgid] = joined
            else:
                catalog[e.msgid] = e.msgstr
        items = sorted(catalog.items())
        ids = b'\x00'.join(k.encode('utf-8') for k, _ in items) + b'\x00'
        strs = b'\x00'.join(v.encode('utf-8') for _, v in items) + b'\x00'
        keystart = 7 * 4 + 16 * len(items)
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        off_id = 0
        off_str = 0
        for k, v in items:
            kb = k.encode('utf-8')
            vb = v.encode('utf-8')
            koffsets.append((len(kb), keystart + off_id))
            voffsets.append((len(vb), valuestart + off_str))
            off_id += len(kb) + 1
            off_str += len(vb) + 1
        with mo_path.open('wb') as out:
            out.write(struct.pack('Iiiiiii', MAGIC, 0, len(items), 7 * 4, 7 * 4 + 8 * len(items), 0, 0))
            for ln, off in koffsets:
                out.write(struct.pack('ii', ln, off))
            for ln, off in voffsets:
                out.write(struct.pack('ii', ln, off))
            out.write(ids)
            out.write(strs)


    def write_mo(self, mo_path: Path, entries: List[POEntry]):
        # Build catalog: msgid -> msgstr (join plurals with NUL)
        catalog = {}
        for e in entries:
            if e.msgid_plural and e.msgstr_plural:
                plural_parts = [e.msgstr_plural.get(i, '') for i in sorted(e.msgstr_plural.keys())]
                catalog[e.msgid] = '\x00'.join(plural_parts)
            else:
                catalog[e.msgid] = e.msgstr
        # Sort by msgid
        items = sorted(catalog.items())
        # Offsets
        ids = b'\x00'.join(s.encode('utf-8') for s,_ in items) + b'\x00'
        strs = b'\x00'.join(t.encode('utf-8') for _,t in items) + b'\x00'
        keystart = 7*4 + 16*len(items)
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        off_id = 0
        off_str = 0
        for k,v in items:
            kbytes = k.encode('utf-8')
            vbytes = v.encode('utf-8')
            koffsets.append((len(kbytes), keystart + off_id))
            voffsets.append((len(vbytes), valuestart + off_str))
            off_id += len(kbytes) + 1
            off_str += len(vbytes) + 1
        with mo_path.open('wb') as out:
            out.write(struct.pack('Iiiiiii', MAGIC, 0, len(items), 7*4, 7*4 + 8*len(items), 0, 0))
            for length, offset in koffsets:
                out.write(struct.pack('ii', length, offset))
            for length, offset in voffsets:
                out.write(struct.pack('ii', length, offset))
            out.write(ids)
            out.write(strs)

