"""Support for line-broken coordinated declaration clauses."""
from __future__ import annotations
from typing import List
DECLARATION_LINE_BREAK = "\x00SYLOPY_DECLARATION_LINE_BREAK\x00"

def _is_declaration_logical_line(logical):
    import re
    text=logical.text.strip(); match=re.match(r"^\s*(?:[0-9]+(?:\.[A-Za-z0-9_]+)*)\.\s*(.*)$",text)
    return bool(match and re.match(r"^let\b",match.group(1).strip(),re.I))

def _patched_prepare_surface_lines(legacy):
    import re
    def comment_preserving_newlines(match: re.Match) -> str:
        return "".join("\n" if ch=="\n" else " " for ch in match.group(0))
    def prepare(text: str):
        cleaned=re.sub(r"\(\*.*?\*\)",comment_preserving_newlines,text,flags=re.S)
        raw_lines=[]; physical=[]
        for line_number,line in enumerate(cleaned.splitlines(),1):
            stripped=line.strip()
            if not stripped or stripped.startswith('#'): continue
            raw_lines.append(line)
            if legacy._is_theory_directive(stripped): continue
            physical.append((line_number,line))
        logical=[]
        for line_number,line in physical:
            stripped=line.strip()
            starts_item=(legacy._LABELED_LINE_RE.match(stripped) or legacy._BEGIN_SUBPROOF_RE.match(stripped) or legacy._END_SUBPROOF_RE.match(stripped))
            if starts_item or not logical:
                logical.append(legacy._LogicalSourceLine(line,line_number,line_number,line)); continue
            previous=logical[-1]
            previous_physical=previous.original_text.splitlines()[-1].strip()
            declaration_break=_is_declaration_logical_line(previous) and previous_physical.endswith(',')
            separator=f" {DECLARATION_LINE_BREAK} " if declaration_break else " "
            logical[-1]=legacy._LogicalSourceLine(previous.text+separator+stripped,previous.start_line,line_number,previous.original_text+'\n'+line)
        return logical,raw_lines
    return prepare

def _patch_splitter(legacy,name):
    original=getattr(legacy,name)
    def split(s):
        if DECLARATION_LINE_BREAK not in s: return original(s)
        result=[]
        for chunk in s.split(DECLARATION_LINE_BREAK):
            chunk=chunk.strip()
            if chunk.endswith(','): chunk=chunk[:-1].rstrip()
            if chunk.lower().startswith('and '): chunk=chunk[4:].lstrip()
            if chunk: result.extend(original(chunk))
        return result
    return split

def install(legacy):
    legacy._prepare_surface_lines=_patched_prepare_surface_lines(legacy)
    legacy.split_declaration_clauses=_patch_splitter(legacy,'split_declaration_clauses')
    legacy._split_compound_declaration_items=_patch_splitter(legacy,'_split_compound_declaration_items')
