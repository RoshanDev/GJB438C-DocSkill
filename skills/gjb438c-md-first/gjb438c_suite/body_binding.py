"""Conservative body-structure and related-resource binding for Word recovery.

A digest is change detection, not a digital signature. TOC bookmark/cache work
is excluded; unexplained body structure or referenced-resource changes are not.
"""
from copy import deepcopy
from hashlib import sha256
import json
import posixpath
from zipfile import ZipFile

from lxml import etree

DOCVAR_STRUCTURE_HASH = 'GJB438C_BODY_STRUCTURE_SHA256'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'w': W}


def body_structure_hash(archive: ZipFile) -> str:
    """Return an empty binding when the body or its dependencies are unresolvable."""
    try:
        root = etree.fromstring(archive.read('word/document.xml'))
        body = root.find('./w:body', NS)
        if body is None:
            return ''
        starts = body.xpath('.//w:bookmarkStart[@w:name="GJB_BODY"]', namespaces=NS)
        if len(starts) != 1:
            return ''
        ends = body.xpath('.//w:bookmarkEnd[@w:id=$id]', namespaces=NS,
                          id=starts[0].get(f'{{{W}}}id'))
        if len(ends) != 1:
            return ''
        def top(element):
            while element.getparent() is not body:
                element = element.getparent()
                if element is None:
                    raise ValueError('body bookmark outside body')
            return body.index(element)
        first, last = top(starts[0]), top(ends[0])
        if first > last:
            return ''
        projection = etree.Element('body-content')
        ignored = {f'{{{W}}}{name}' for name in (
            'bookmarkStart', 'bookmarkEnd', 'proofErr', 'lastRenderedPageBreak')}
        # Include content appended beyond the closing bookmark as a change;
        # it must never be silently classified as the old preserved body.
        for child in list(body)[first:]:
            clone = deepcopy(child)
            for node in list(clone.iter()):
                if node.tag in ignored:
                    node.getparent().remove(node)
                    continue
                for name in list(node.attrib):
                    local = etree.QName(name).localname
                    if local.startswith('rsid') or local in {'paraId', 'textId'}:
                        del node.attrib[name]
            projection.append(clone)
        records = {'body': sha256(etree.tostring(
            projection, method='c14n', exclusive=True, with_comments=False)).hexdigest()}
        names = set(archive.namelist())
        seen = set()
        def relations(part):
            path = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
            if path not in names:
                return {}
            relroot = etree.fromstring(archive.read(path))
            result = {}
            for rel in relroot.findall(f'{{{P}}}Relationship'):
                ident = rel.get('Id')
                if not ident or ident in result:
                    raise ValueError('ambiguous relationship')
                result[ident] = rel
            return result
        def dependency(part, ident, rel):
            target = rel.get('Target', '')
            mode = rel.get('TargetMode', 'Internal')
            records[f'rel:{part}:{ident}'] = [rel.get('Type'), mode, target]
            if not target:
                raise ValueError('missing relationship target')
            if mode == 'External':
                # A link destination is data; externally mutable media is not
                # available to verify and cannot qualify for exact recovery.
                if not str(rel.get('Type', '')).endswith('/hyperlink'):
                    raise ValueError('external body resource cannot be verified')
                return
            destination = posixpath.normpath(target.lstrip('/') if target.startswith('/') else
                                             posixpath.join(posixpath.dirname(part), target))
            if destination.startswith('../'):
                raise ValueError('relationship escapes package')
            bind_part(destination)
        def bind_part(part):
            if part in seen:
                return
            seen.add(part)
            records[f'part:{part}'] = sha256(archive.read(part)).hexdigest()
            for ident, rel in relations(part).items():
                dependency(part, ident, rel)
        document_relations = relations('word/document.xml')
        rids = {value for node in projection.iter() for name, value in node.attrib.items()
                if name.startswith('{' + R + '}')}
        for ident in sorted(rids):
            if ident not in document_relations:
                raise ValueError('unresolved body relationship')
            dependency('word/document.xml', ident, document_relations[ident])
        # Indirect formatting definitions affect table geometry and hierarchy.
        for part in ('word/styles.xml', 'word/numbering.xml', 'word/theme/theme1.xml'):
            if part in names:
                bind_part(part)
        return sha256(json.dumps(records, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    except (KeyError, ValueError, TypeError, etree.XMLSyntaxError):
        return ''
