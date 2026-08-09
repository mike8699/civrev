#!/usr/bin/env python3
"""xrefs for CivRev PS3 EBOOT_v100.ELF (vaddr = fileoff + 0x10000, TOC r2=0x1929e20)"""
import sys, struct, array, bisect, os, re

BASE = '/home/mike/Desktop/civrev/civrev_ps3'
ELF = os.path.join(BASE, 'EBOOT_v100.ELF')
D = open(ELF, 'rb').read()
TOC = 0x1929e20
TEXT_START = 0x10000
TEXT_SIZE = 0x1843d48
DELTA = 0x10000  # vaddr = fileoff + DELTA

def f2v(o): return o + DELTA
def v2f(v): return v - DELTA
def u32(v): return struct.unpack('>I', D[v2f(v):v2f(v)+4])[0]
def cstr(v):
    o = v2f(v); e = D.find(b'\0', o); return D[o:e].decode('latin1', 'replace')

W = array.array('I'); W.frombytes(D[0:TEXT_SIZE]); W.byteswap()

# function starts from decompiled export filenames
_fa = None
def funcs():
    global _fa
    if _fa is None:
        dd = os.path.join(BASE, 'decompiled')
        _fa = sorted(int(n.split('_')[0], 16) for n in os.listdir(dd) if n.endswith('.c'))
    return _fa

def fn_of(addr):
    a = funcs(); i = bisect.bisect_right(a, addr) - 1
    return a[i] if i >= 0 else None

def s16(x): return x - 0x10000 if x & 0x8000 else x

# Build TOC-slot -> [code addrs] index once
_toc_refs = None
def toc_index():
    """map: TOC slot vaddr -> list of instruction vaddrs (lwz rX, D(r2))"""
    global _toc_refs
    if _toc_refs is None:
        m = {}
        hi = [None]*32   # register -> base value from addis rX,r2,N (or lis)
        for i, x in enumerate(W):
            a = TEXT_START + i*4
            op = x >> 26; rt = (x >> 21) & 31; ra = (x >> 16) & 31; dd = x & 0xffff
            if op == 15:            # addis
                if ra == 2:   hi[rt] = (TOC + (s16(dd) << 16)) & 0xffffffff
                elif ra == 0: hi[rt] = (s16(dd) << 16) & 0xffffffff
                elif hi[ra] is not None: hi[rt] = (hi[ra] + (s16(dd) << 16)) & 0xffffffff
                else: hi[rt] = None
            elif op == 32:          # lwz rT, D(rA)
                base = TOC if ra == 2 else hi[ra]
                if base is not None:
                    m.setdefault((base + s16(dd)) & 0xffffffff, []).append(a)
                if rt != ra: hi[rt] = None
            elif op == 14:          # addi
                base = 0 if ra == 0 else hi[ra]
                hi[rt] = None if base is None else (base + s16(dd)) & 0xffffffff
            elif op == 18:          # b/bl -> clear volatile scratch
                hi = [None]*32
            else:
                if op in (7,8,12,13,24,25,26,27,28,29,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,58,62):
                    hi[rt] = None
                elif op == 31:
                    hi[rt] = None
        _toc_refs = m
    return _toc_refs

def find_ptr_slots(target):
    """find data words in whole file equal to target -> vaddrs"""
    p = struct.pack('>I', target); out = []; i = D.find(p)
    while i != -1:
        out.append(f2v(i)); i = D.find(p, i+1)
    return out

def str_xrefs(target_vaddr):
    """returns list of (instr_addr, func_addr, slot)"""
    res = []
    ti = toc_index()
    for slot in find_ptr_slots(target_vaddr):
        for ia in ti.get(slot, []):
            res.append((ia, fn_of(ia), slot))
    return res

def bl_callers(target):
    """find bl instructions targeting `target`"""
    out = []
    for i, x in enumerate(W):
        if (x >> 26) == 18:  # b/bl
            li = x & 0x03fffffc
            if li & 0x02000000: li -= 0x04000000
            aa = x & 2; lk = x & 1
            a = TEXT_START + i*4
            tgt = li if aa else a + li
            if tgt == target and lk:
                out.append((a, fn_of(a)))
    return out

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'str':
        v = int(sys.argv[2], 16)
        print('string:', repr(cstr(v)))
        for ia, fa, slot in str_xrefs(v):
            print('  ref @ %08x  in FUN_%08x  (toc slot %08x)' % (ia, fa or 0, slot))
    elif cmd == 'callers':
        t = int(sys.argv[2], 16)
        seen = {}
        for a, fa in bl_callers(t):
            seen.setdefault(fa, []).append(a)
        for fa, sites in sorted(seen.items()):
            print('FUN_%08x  sites: %s' % (fa or 0, ' '.join('%08x' % s for s in sites)))
    elif cmd == 'ptrtab':
        v = int(sys.argv[2], 16); n = int(sys.argv[3]) if len(sys.argv) > 3 else 32
        for a in range(v, v + n*4, 4):
            x = u32(a); s = ''
            if 0x100000 < x < 0x1853d48:
                t = cstr(x)
                if t and all(32 <= ord(c) < 127 for c in t[:48]): s = repr(t[:70])
            print('%08x: %08x %s' % (a, x, s))

# ---- multi-TOC support ----
_opd = None
def opd_map():
    """func entry vaddr -> toc base, from OPD section 0x18a5a70..0x1921e20"""
    global _opd
    if _opd is None:
        m = {}
        for v in range(0x18a5a70, 0x1921e20, 8):
            fa = u32(v); tc = u32(v+4)
            if 0x10000 <= fa < 0x1853d48 and tc in (0x1929e20, 0x1939d98, 0x1949d58):
                m[fa] = tc
        _opd = m
    return _opd

_ftoc = None
def func_toc(addr):
    """TOC in effect at a code address (by containing function)"""
    global _ftoc
    if _ftoc is None:
        om = opd_map(); _ftoc = {}
        for fa in funcs():
            if fa in om: _ftoc[fa] = om[fa]
        # propagate: functions without OPD inherit nearest preceding known
        prev = 0x1929e20
        for fa in funcs():
            if fa in _ftoc: prev = _ftoc[fa]
            else: _ftoc[fa] = prev
    fa = fn_of(addr)
    return _ftoc.get(fa, 0x1929e20)

_mref = None
def mtoc_index():
    """slot vaddr -> [code addrs], resolving r2 per containing function, plus addis+lwz"""
    global _mref
    if _mref is None:
        m = {}
        fa_list = funcs()
        import bisect as _b
        cur_toc = 0x1929e20; nxt = 0
        hi = [None]*32
        for i, x in enumerate(W):
            a = TEXT_START + i*4
            if nxt < len(fa_list) and a == fa_list[nxt]:
                cur_toc = func_toc(a); nxt += 1; hi = [None]*32
            elif nxt < len(fa_list) and a > fa_list[nxt]:
                while nxt < len(fa_list) and fa_list[nxt] <= a: nxt += 1
            op = x >> 26; rt = (x >> 21) & 31; ra = (x >> 16) & 31; dd = x & 0xffff
            if op == 15:
                if ra == 2: hi[rt] = (cur_toc + (s16(dd) << 16)) & 0xffffffff
                elif ra == 0: hi[rt] = (s16(dd) << 16) & 0xffffffff
                else: hi[rt] = None
            elif op == 32:
                base = cur_toc if ra == 2 else hi[ra]
                if base is not None:
                    m.setdefault((base + s16(dd)) & 0xffffffff, []).append(a)
                if rt != ra: hi[rt] = None
            elif op == 14:
                base = 0 if ra == 0 else hi[ra]
                hi[rt] = None if base is None else (base + s16(dd)) & 0xffffffff
            else:
                hi[rt] = None
        _mref = m
    return _mref

def mstr_xrefs(target_vaddr):
    res = []; ti = mtoc_index()
    for slot in find_ptr_slots(target_vaddr):
        for ia in ti.get(slot, []):
            res.append((ia, fn_of(ia), slot))
    return res

def fn_end(fa):
    a = funcs(); i = bisect.bisect_right(a, fa)
    return a[i] if i < len(a) else 0x1853d48

def fn_slots(fa):
    """all TOC-relative loads inside function fa, resolved with its own TOC"""
    toc = func_toc(fa); end = fn_end(fa)
    out = []; hi = [None]*32
    for a in range(fa, end, 4):
        x = W[(a - TEXT_START)//4]
        op = x >> 26; rt = (x>>21)&31; ra = (x>>16)&31; dd = x & 0xffff
        if op == 15:
            hi[rt] = (toc + (s16(dd)<<16)) & 0xffffffff if ra == 2 else None
        elif op in (32,48,50,58,36,52,54):
            base = toc if ra == 2 else hi[ra]
            if base is not None:
                slot = (base + s16(dd)) & 0xffffffff
                ghidra = slot - (toc - 0x1929e20)
                val = u32(slot) if 0x1860000 <= slot < 0x196b178 else None
                s = ''
                if val and 0x100000 < val < 0x1853d48:
                    t = cstr(val)
                    if t and all(32 <= ord(c) < 127 for c in t[:48]): s = repr(t[:60])
                out.append((a, slot, ghidra, val, s))
            if op == 32 and rt != ra: hi[rt] = None
        else:
            hi[rt] = None
    return toc, out
