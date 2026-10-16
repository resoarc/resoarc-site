/*
ResoArc Backup & Migration 0.3 alpha (MIT)
Includes fflate 0.8.2, licensed under the MIT License:

MIT License

Copyright (c) 2023 Arjun Barrett

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
(() => {
  // node_modules/fflate/esm/browser.js
  var u8 = Uint8Array;
  var u16 = Uint16Array;
  var i32 = Int32Array;
  var fleb = new u8([
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    2,
    2,
    2,
    2,
    3,
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    5,
    5,
    5,
    5,
    0,
    /* unused */
    0,
    0,
    /* impossible */
    0
  ]);
  var fdeb = new u8([
    0,
    0,
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    4,
    5,
    5,
    6,
    6,
    7,
    7,
    8,
    8,
    9,
    9,
    10,
    10,
    11,
    11,
    12,
    12,
    13,
    13,
    /* unused */
    0,
    0
  ]);
  var clim = new u8([16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]);
  var freb = function(eb, start) {
    var b = new u16(31);
    for (var i = 0; i < 31; ++i) {
      b[i] = start += 1 << eb[i - 1];
    }
    var r = new i32(b[30]);
    for (var i = 1; i < 30; ++i) {
      for (var j = b[i]; j < b[i + 1]; ++j) {
        r[j] = j - b[i] << 5 | i;
      }
    }
    return { b, r };
  };
  var _a = freb(fleb, 2);
  var fl = _a.b;
  var revfl = _a.r;
  fl[28] = 258, revfl[258] = 28;
  var _b = freb(fdeb, 0);
  var fd = _b.b;
  var revfd = _b.r;
  var rev = new u16(32768);
  for (i = 0; i < 32768; ++i) {
    x = (i & 43690) >> 1 | (i & 21845) << 1;
    x = (x & 52428) >> 2 | (x & 13107) << 2;
    x = (x & 61680) >> 4 | (x & 3855) << 4;
    rev[i] = ((x & 65280) >> 8 | (x & 255) << 8) >> 1;
  }
  var x;
  var i;
  var hMap = (function(cd, mb, r) {
    var s2 = cd.length;
    var i = 0;
    var l = new u16(mb);
    for (; i < s2; ++i) {
      if (cd[i])
        ++l[cd[i] - 1];
    }
    var le = new u16(mb);
    for (i = 1; i < mb; ++i) {
      le[i] = le[i - 1] + l[i - 1] << 1;
    }
    var co;
    if (r) {
      co = new u16(1 << mb);
      var rvb = 15 - mb;
      for (i = 0; i < s2; ++i) {
        if (cd[i]) {
          var sv = i << 4 | cd[i];
          var r_1 = mb - cd[i];
          var v = le[cd[i] - 1]++ << r_1;
          for (var m = v | (1 << r_1) - 1; v <= m; ++v) {
            co[rev[v] >> rvb] = sv;
          }
        }
      }
    } else {
      co = new u16(s2);
      for (i = 0; i < s2; ++i) {
        if (cd[i]) {
          co[i] = rev[le[cd[i] - 1]++] >> 15 - cd[i];
        }
      }
    }
    return co;
  });
  var flt = new u8(288);
  for (i = 0; i < 144; ++i)
    flt[i] = 8;
  var i;
  for (i = 144; i < 256; ++i)
    flt[i] = 9;
  var i;
  for (i = 256; i < 280; ++i)
    flt[i] = 7;
  var i;
  for (i = 280; i < 288; ++i)
    flt[i] = 8;
  var i;
  var fdt = new u8(32);
  for (i = 0; i < 32; ++i)
    fdt[i] = 5;
  var i;
  var flm = /* @__PURE__ */ hMap(flt, 9, 0);
  var flrm = /* @__PURE__ */ hMap(flt, 9, 1);
  var fdm = /* @__PURE__ */ hMap(fdt, 5, 0);
  var fdrm = /* @__PURE__ */ hMap(fdt, 5, 1);
  var max = function(a) {
    var m = a[0];
    for (var i = 1; i < a.length; ++i) {
      if (a[i] > m)
        m = a[i];
    }
    return m;
  };
  var bits = function(d, p, m) {
    var o = p / 8 | 0;
    return (d[o] | d[o + 1] << 8) >> (p & 7) & m;
  };
  var bits16 = function(d, p) {
    var o = p / 8 | 0;
    return (d[o] | d[o + 1] << 8 | d[o + 2] << 16) >> (p & 7);
  };
  var shft = function(p) {
    return (p + 7) / 8 | 0;
  };
  var slc = function(v, s2, e) {
    if (s2 == null || s2 < 0)
      s2 = 0;
    if (e == null || e > v.length)
      e = v.length;
    return new u8(v.subarray(s2, e));
  };
  var ec = [
    "unexpected EOF",
    "invalid block type",
    "invalid length/literal",
    "invalid distance",
    "stream finished",
    "no stream handler",
    ,
    "no callback",
    "invalid UTF-8 data",
    "extra field too long",
    "date not in range 1980-2099",
    "filename too long",
    "stream finishing",
    "invalid zip data"
    // determined by unknown compression method
  ];
  var err = function(ind, msg, nt) {
    var e = new Error(msg || ec[ind]);
    e.code = ind;
    if (Error.captureStackTrace)
      Error.captureStackTrace(e, err);
    if (!nt)
      throw e;
    return e;
  };
  var inflt = function(dat, st, buf, dict) {
    var sl = dat.length, dl = dict ? dict.length : 0;
    if (!sl || st.f && !st.l)
      return buf || new u8(0);
    var noBuf = !buf;
    var resize = noBuf || st.i != 2;
    var noSt = st.i;
    if (noBuf)
      buf = new u8(sl * 3);
    var cbuf = function(l2) {
      var bl = buf.length;
      if (l2 > bl) {
        var nbuf = new u8(Math.max(bl * 2, l2));
        nbuf.set(buf);
        buf = nbuf;
      }
    };
    var final = st.f || 0, pos = st.p || 0, bt = st.b || 0, lm = st.l, dm = st.d, lbt = st.m, dbt = st.n;
    var tbts = sl * 8;
    do {
      if (!lm) {
        final = bits(dat, pos, 1);
        var type = bits(dat, pos + 1, 3);
        pos += 3;
        if (!type) {
          var s2 = shft(pos) + 4, l = dat[s2 - 4] | dat[s2 - 3] << 8, t = s2 + l;
          if (t > sl) {
            if (noSt)
              err(0);
            break;
          }
          if (resize)
            cbuf(bt + l);
          buf.set(dat.subarray(s2, t), bt);
          st.b = bt += l, st.p = pos = t * 8, st.f = final;
          continue;
        } else if (type == 1)
          lm = flrm, dm = fdrm, lbt = 9, dbt = 5;
        else if (type == 2) {
          var hLit = bits(dat, pos, 31) + 257, hcLen = bits(dat, pos + 10, 15) + 4;
          var tl = hLit + bits(dat, pos + 5, 31) + 1;
          pos += 14;
          var ldt = new u8(tl);
          var clt = new u8(19);
          for (var i = 0; i < hcLen; ++i) {
            clt[clim[i]] = bits(dat, pos + i * 3, 7);
          }
          pos += hcLen * 3;
          var clb = max(clt), clbmsk = (1 << clb) - 1;
          var clm = hMap(clt, clb, 1);
          for (var i = 0; i < tl; ) {
            var r = clm[bits(dat, pos, clbmsk)];
            pos += r & 15;
            var s2 = r >> 4;
            if (s2 < 16) {
              ldt[i++] = s2;
            } else {
              var c = 0, n = 0;
              if (s2 == 16)
                n = 3 + bits(dat, pos, 3), pos += 2, c = ldt[i - 1];
              else if (s2 == 17)
                n = 3 + bits(dat, pos, 7), pos += 3;
              else if (s2 == 18)
                n = 11 + bits(dat, pos, 127), pos += 7;
              while (n--)
                ldt[i++] = c;
            }
          }
          var lt = ldt.subarray(0, hLit), dt = ldt.subarray(hLit);
          lbt = max(lt);
          dbt = max(dt);
          lm = hMap(lt, lbt, 1);
          dm = hMap(dt, dbt, 1);
        } else
          err(1);
        if (pos > tbts) {
          if (noSt)
            err(0);
          break;
        }
      }
      if (resize)
        cbuf(bt + 131072);
      var lms = (1 << lbt) - 1, dms = (1 << dbt) - 1;
      var lpos = pos;
      for (; ; lpos = pos) {
        var c = lm[bits16(dat, pos) & lms], sym = c >> 4;
        pos += c & 15;
        if (pos > tbts) {
          if (noSt)
            err(0);
          break;
        }
        if (!c)
          err(2);
        if (sym < 256)
          buf[bt++] = sym;
        else if (sym == 256) {
          lpos = pos, lm = null;
          break;
        } else {
          var add = sym - 254;
          if (sym > 264) {
            var i = sym - 257, b = fleb[i];
            add = bits(dat, pos, (1 << b) - 1) + fl[i];
            pos += b;
          }
          var d = dm[bits16(dat, pos) & dms], dsym = d >> 4;
          if (!d)
            err(3);
          pos += d & 15;
          var dt = fd[dsym];
          if (dsym > 3) {
            var b = fdeb[dsym];
            dt += bits16(dat, pos) & (1 << b) - 1, pos += b;
          }
          if (pos > tbts) {
            if (noSt)
              err(0);
            break;
          }
          if (resize)
            cbuf(bt + 131072);
          var end = bt + add;
          if (bt < dt) {
            var shift = dl - dt, dend = Math.min(dt, end);
            if (shift + bt < 0)
              err(3);
            for (; bt < dend; ++bt)
              buf[bt] = dict[shift + bt];
          }
          for (; bt < end; ++bt)
            buf[bt] = buf[bt - dt];
        }
      }
      st.l = lm, st.p = lpos, st.b = bt, st.f = final;
      if (lm)
        final = 1, st.m = lbt, st.d = dm, st.n = dbt;
    } while (!final);
    return bt != buf.length && noBuf ? slc(buf, 0, bt) : buf.subarray(0, bt);
  };
  var wbits = function(d, p, v) {
    v <<= p & 7;
    var o = p / 8 | 0;
    d[o] |= v;
    d[o + 1] |= v >> 8;
  };
  var wbits16 = function(d, p, v) {
    v <<= p & 7;
    var o = p / 8 | 0;
    d[o] |= v;
    d[o + 1] |= v >> 8;
    d[o + 2] |= v >> 16;
  };
  var hTree = function(d, mb) {
    var t = [];
    for (var i = 0; i < d.length; ++i) {
      if (d[i])
        t.push({ s: i, f: d[i] });
    }
    var s2 = t.length;
    var t2 = t.slice();
    if (!s2)
      return { t: et, l: 0 };
    if (s2 == 1) {
      var v = new u8(t[0].s + 1);
      v[t[0].s] = 1;
      return { t: v, l: 1 };
    }
    t.sort(function(a, b) {
      return a.f - b.f;
    });
    t.push({ s: -1, f: 25001 });
    var l = t[0], r = t[1], i0 = 0, i1 = 1, i2 = 2;
    t[0] = { s: -1, f: l.f + r.f, l, r };
    while (i1 != s2 - 1) {
      l = t[t[i0].f < t[i2].f ? i0++ : i2++];
      r = t[i0 != i1 && t[i0].f < t[i2].f ? i0++ : i2++];
      t[i1++] = { s: -1, f: l.f + r.f, l, r };
    }
    var maxSym = t2[0].s;
    for (var i = 1; i < s2; ++i) {
      if (t2[i].s > maxSym)
        maxSym = t2[i].s;
    }
    var tr = new u16(maxSym + 1);
    var mbt = ln(t[i1 - 1], tr, 0);
    if (mbt > mb) {
      var i = 0, dt = 0;
      var lft = mbt - mb, cst = 1 << lft;
      t2.sort(function(a, b) {
        return tr[b.s] - tr[a.s] || a.f - b.f;
      });
      for (; i < s2; ++i) {
        var i2_1 = t2[i].s;
        if (tr[i2_1] > mb) {
          dt += cst - (1 << mbt - tr[i2_1]);
          tr[i2_1] = mb;
        } else
          break;
      }
      dt >>= lft;
      while (dt > 0) {
        var i2_2 = t2[i].s;
        if (tr[i2_2] < mb)
          dt -= 1 << mb - tr[i2_2]++ - 1;
        else
          ++i;
      }
      for (; i >= 0 && dt; --i) {
        var i2_3 = t2[i].s;
        if (tr[i2_3] == mb) {
          --tr[i2_3];
          ++dt;
        }
      }
      mbt = mb;
    }
    return { t: new u8(tr), l: mbt };
  };
  var ln = function(n, l, d) {
    return n.s == -1 ? Math.max(ln(n.l, l, d + 1), ln(n.r, l, d + 1)) : l[n.s] = d;
  };
  var lc = function(c) {
    var s2 = c.length;
    while (s2 && !c[--s2])
      ;
    var cl = new u16(++s2);
    var cli = 0, cln = c[0], cls = 1;
    var w = function(v) {
      cl[cli++] = v;
    };
    for (var i = 1; i <= s2; ++i) {
      if (c[i] == cln && i != s2)
        ++cls;
      else {
        if (!cln && cls > 2) {
          for (; cls > 138; cls -= 138)
            w(32754);
          if (cls > 2) {
            w(cls > 10 ? cls - 11 << 5 | 28690 : cls - 3 << 5 | 12305);
            cls = 0;
          }
        } else if (cls > 3) {
          w(cln), --cls;
          for (; cls > 6; cls -= 6)
            w(8304);
          if (cls > 2)
            w(cls - 3 << 5 | 8208), cls = 0;
        }
        while (cls--)
          w(cln);
        cls = 1;
        cln = c[i];
      }
    }
    return { c: cl.subarray(0, cli), n: s2 };
  };
  var clen = function(cf, cl) {
    var l = 0;
    for (var i = 0; i < cl.length; ++i)
      l += cf[i] * cl[i];
    return l;
  };
  var wfblk = function(out, pos, dat) {
    var s2 = dat.length;
    var o = shft(pos + 2);
    out[o] = s2 & 255;
    out[o + 1] = s2 >> 8;
    out[o + 2] = out[o] ^ 255;
    out[o + 3] = out[o + 1] ^ 255;
    for (var i = 0; i < s2; ++i)
      out[o + i + 4] = dat[i];
    return (o + 4 + s2) * 8;
  };
  var wblk = function(dat, out, final, syms, lf, df, eb, li, bs, bl, p) {
    wbits(out, p++, final);
    ++lf[256];
    var _a2 = hTree(lf, 15), dlt = _a2.t, mlb = _a2.l;
    var _b2 = hTree(df, 15), ddt = _b2.t, mdb = _b2.l;
    var _c = lc(dlt), lclt = _c.c, nlc = _c.n;
    var _d = lc(ddt), lcdt = _d.c, ndc = _d.n;
    var lcfreq = new u16(19);
    for (var i = 0; i < lclt.length; ++i)
      ++lcfreq[lclt[i] & 31];
    for (var i = 0; i < lcdt.length; ++i)
      ++lcfreq[lcdt[i] & 31];
    var _e = hTree(lcfreq, 7), lct = _e.t, mlcb = _e.l;
    var nlcc = 19;
    for (; nlcc > 4 && !lct[clim[nlcc - 1]]; --nlcc)
      ;
    var flen = bl + 5 << 3;
    var ftlen = clen(lf, flt) + clen(df, fdt) + eb;
    var dtlen = clen(lf, dlt) + clen(df, ddt) + eb + 14 + 3 * nlcc + clen(lcfreq, lct) + 2 * lcfreq[16] + 3 * lcfreq[17] + 7 * lcfreq[18];
    if (bs >= 0 && flen <= ftlen && flen <= dtlen)
      return wfblk(out, p, dat.subarray(bs, bs + bl));
    var lm, ll, dm, dl;
    wbits(out, p, 1 + (dtlen < ftlen)), p += 2;
    if (dtlen < ftlen) {
      lm = hMap(dlt, mlb, 0), ll = dlt, dm = hMap(ddt, mdb, 0), dl = ddt;
      var llm = hMap(lct, mlcb, 0);
      wbits(out, p, nlc - 257);
      wbits(out, p + 5, ndc - 1);
      wbits(out, p + 10, nlcc - 4);
      p += 14;
      for (var i = 0; i < nlcc; ++i)
        wbits(out, p + 3 * i, lct[clim[i]]);
      p += 3 * nlcc;
      var lcts = [lclt, lcdt];
      for (var it = 0; it < 2; ++it) {
        var clct = lcts[it];
        for (var i = 0; i < clct.length; ++i) {
          var len = clct[i] & 31;
          wbits(out, p, llm[len]), p += lct[len];
          if (len > 15)
            wbits(out, p, clct[i] >> 5 & 127), p += clct[i] >> 12;
        }
      }
    } else {
      lm = flm, ll = flt, dm = fdm, dl = fdt;
    }
    for (var i = 0; i < li; ++i) {
      var sym = syms[i];
      if (sym > 255) {
        var len = sym >> 18 & 31;
        wbits16(out, p, lm[len + 257]), p += ll[len + 257];
        if (len > 7)
          wbits(out, p, sym >> 23 & 31), p += fleb[len];
        var dst = sym & 31;
        wbits16(out, p, dm[dst]), p += dl[dst];
        if (dst > 3)
          wbits16(out, p, sym >> 5 & 8191), p += fdeb[dst];
      } else {
        wbits16(out, p, lm[sym]), p += ll[sym];
      }
    }
    wbits16(out, p, lm[256]);
    return p + ll[256];
  };
  var deo = /* @__PURE__ */ new i32([65540, 131080, 131088, 131104, 262176, 1048704, 1048832, 2114560, 2117632]);
  var et = /* @__PURE__ */ new u8(0);
  var dflt = function(dat, lvl, plvl, pre, post, st) {
    var s2 = st.z || dat.length;
    var o = new u8(pre + s2 + 5 * (1 + Math.ceil(s2 / 7e3)) + post);
    var w = o.subarray(pre, o.length - post);
    var lst = st.l;
    var pos = (st.r || 0) & 7;
    if (lvl) {
      if (pos)
        w[0] = st.r >> 3;
      var opt = deo[lvl - 1];
      var n = opt >> 13, c = opt & 8191;
      var msk_1 = (1 << plvl) - 1;
      var prev = st.p || new u16(32768), head = st.h || new u16(msk_1 + 1);
      var bs1_1 = Math.ceil(plvl / 3), bs2_1 = 2 * bs1_1;
      var hsh = function(i2) {
        return (dat[i2] ^ dat[i2 + 1] << bs1_1 ^ dat[i2 + 2] << bs2_1) & msk_1;
      };
      var syms = new i32(25e3);
      var lf = new u16(288), df = new u16(32);
      var lc_1 = 0, eb = 0, i = st.i || 0, li = 0, wi = st.w || 0, bs = 0;
      for (; i + 2 < s2; ++i) {
        var hv = hsh(i);
        var imod = i & 32767, pimod = head[hv];
        prev[imod] = pimod;
        head[hv] = imod;
        if (wi <= i) {
          var rem = s2 - i;
          if ((lc_1 > 7e3 || li > 24576) && (rem > 423 || !lst)) {
            pos = wblk(dat, w, 0, syms, lf, df, eb, li, bs, i - bs, pos);
            li = lc_1 = eb = 0, bs = i;
            for (var j = 0; j < 286; ++j)
              lf[j] = 0;
            for (var j = 0; j < 30; ++j)
              df[j] = 0;
          }
          var l = 2, d = 0, ch_1 = c, dif = imod - pimod & 32767;
          if (rem > 2 && hv == hsh(i - dif)) {
            var maxn = Math.min(n, rem) - 1;
            var maxd = Math.min(32767, i);
            var ml = Math.min(258, rem);
            while (dif <= maxd && --ch_1 && imod != pimod) {
              if (dat[i + l] == dat[i + l - dif]) {
                var nl = 0;
                for (; nl < ml && dat[i + nl] == dat[i + nl - dif]; ++nl)
                  ;
                if (nl > l) {
                  l = nl, d = dif;
                  if (nl > maxn)
                    break;
                  var mmd = Math.min(dif, nl - 2);
                  var md = 0;
                  for (var j = 0; j < mmd; ++j) {
                    var ti = i - dif + j & 32767;
                    var pti = prev[ti];
                    var cd = ti - pti & 32767;
                    if (cd > md)
                      md = cd, pimod = ti;
                  }
                }
              }
              imod = pimod, pimod = prev[imod];
              dif += imod - pimod & 32767;
            }
          }
          if (d) {
            syms[li++] = 268435456 | revfl[l] << 18 | revfd[d];
            var lin = revfl[l] & 31, din = revfd[d] & 31;
            eb += fleb[lin] + fdeb[din];
            ++lf[257 + lin];
            ++df[din];
            wi = i + l;
            ++lc_1;
          } else {
            syms[li++] = dat[i];
            ++lf[dat[i]];
          }
        }
      }
      for (i = Math.max(i, wi); i < s2; ++i) {
        syms[li++] = dat[i];
        ++lf[dat[i]];
      }
      pos = wblk(dat, w, lst, syms, lf, df, eb, li, bs, i - bs, pos);
      if (!lst) {
        st.r = pos & 7 | w[pos / 8 | 0] << 3;
        pos -= 7;
        st.h = head, st.p = prev, st.i = i, st.w = wi;
      }
    } else {
      for (var i = st.w || 0; i < s2 + lst; i += 65535) {
        var e = i + 65535;
        if (e >= s2) {
          w[pos / 8 | 0] = lst;
          e = s2;
        }
        pos = wfblk(w, pos + 1, dat.subarray(i, e));
      }
      st.i = s2;
    }
    return slc(o, 0, pre + shft(pos) + post);
  };
  var crct = /* @__PURE__ */ (function() {
    var t = new Int32Array(256);
    for (var i = 0; i < 256; ++i) {
      var c = i, k = 9;
      while (--k)
        c = (c & 1 && -306674912) ^ c >>> 1;
      t[i] = c;
    }
    return t;
  })();
  var crc = function() {
    var c = -1;
    return {
      p: function(d) {
        var cr = c;
        for (var i = 0; i < d.length; ++i)
          cr = crct[cr & 255 ^ d[i]] ^ cr >>> 8;
        c = cr;
      },
      d: function() {
        return ~c;
      }
    };
  };
  var dopt = function(dat, opt, pre, post, st) {
    if (!st) {
      st = { l: 1 };
      if (opt.dictionary) {
        var dict = opt.dictionary.subarray(-32768);
        var newDat = new u8(dict.length + dat.length);
        newDat.set(dict);
        newDat.set(dat, dict.length);
        dat = newDat;
        st.w = dict.length;
      }
    }
    return dflt(dat, opt.level == null ? 6 : opt.level, opt.mem == null ? st.l ? Math.ceil(Math.max(8, Math.min(13, Math.log(dat.length))) * 1.5) : 20 : 12 + opt.mem, pre, post, st);
  };
  var mrg = function(a, b) {
    var o = {};
    for (var k in a)
      o[k] = a[k];
    for (var k in b)
      o[k] = b[k];
    return o;
  };
  var b2 = function(d, b) {
    return d[b] | d[b + 1] << 8;
  };
  var b4 = function(d, b) {
    return (d[b] | d[b + 1] << 8 | d[b + 2] << 16 | d[b + 3] << 24) >>> 0;
  };
  var b8 = function(d, b) {
    return b4(d, b) + b4(d, b + 4) * 4294967296;
  };
  var wbytes = function(d, b, v) {
    for (; v; ++b)
      d[b] = v, v >>>= 8;
  };
  function deflateSync(data, opts) {
    return dopt(data, opts || {}, 0, 0);
  }
  function inflateSync(data, opts) {
    return inflt(data, { i: 2 }, opts && opts.out, opts && opts.dictionary);
  }
  var fltn = function(d, p, t, o) {
    for (var k in d) {
      var val = d[k], n = p + k, op = o;
      if (Array.isArray(val))
        op = mrg(o, val[1]), val = val[0];
      if (val instanceof u8)
        t[n] = [val, op];
      else {
        t[n += "/"] = [new u8(0), op];
        fltn(val, n, t, o);
      }
    }
  };
  var te = typeof TextEncoder != "undefined" && /* @__PURE__ */ new TextEncoder();
  var td = typeof TextDecoder != "undefined" && /* @__PURE__ */ new TextDecoder();
  var tds = 0;
  try {
    td.decode(et, { stream: true });
    tds = 1;
  } catch (e) {
  }
  var dutf8 = function(d) {
    for (var r = "", i = 0; ; ) {
      var c = d[i++];
      var eb = (c > 127) + (c > 223) + (c > 239);
      if (i + eb > d.length)
        return { s: r, r: slc(d, i - 1) };
      if (!eb)
        r += String.fromCharCode(c);
      else if (eb == 3) {
        c = ((c & 15) << 18 | (d[i++] & 63) << 12 | (d[i++] & 63) << 6 | d[i++] & 63) - 65536, r += String.fromCharCode(55296 | c >> 10, 56320 | c & 1023);
      } else if (eb & 1)
        r += String.fromCharCode((c & 31) << 6 | d[i++] & 63);
      else
        r += String.fromCharCode((c & 15) << 12 | (d[i++] & 63) << 6 | d[i++] & 63);
    }
  };
  function strToU8(str2, latin1) {
    if (latin1) {
      var ar_1 = new u8(str2.length);
      for (var i = 0; i < str2.length; ++i)
        ar_1[i] = str2.charCodeAt(i);
      return ar_1;
    }
    if (te)
      return te.encode(str2);
    var l = str2.length;
    var ar = new u8(str2.length + (str2.length >> 1));
    var ai = 0;
    var w = function(v) {
      ar[ai++] = v;
    };
    for (var i = 0; i < l; ++i) {
      if (ai + 5 > ar.length) {
        var n = new u8(ai + 8 + (l - i << 1));
        n.set(ar);
        ar = n;
      }
      var c = str2.charCodeAt(i);
      if (c < 128 || latin1)
        w(c);
      else if (c < 2048)
        w(192 | c >> 6), w(128 | c & 63);
      else if (c > 55295 && c < 57344)
        c = 65536 + (c & 1023 << 10) | str2.charCodeAt(++i) & 1023, w(240 | c >> 18), w(128 | c >> 12 & 63), w(128 | c >> 6 & 63), w(128 | c & 63);
      else
        w(224 | c >> 12), w(128 | c >> 6 & 63), w(128 | c & 63);
    }
    return slc(ar, 0, ai);
  }
  function strFromU8(dat, latin1) {
    if (latin1) {
      var r = "";
      for (var i = 0; i < dat.length; i += 16384)
        r += String.fromCharCode.apply(null, dat.subarray(i, i + 16384));
      return r;
    } else if (td) {
      return td.decode(dat);
    } else {
      var _a2 = dutf8(dat), s2 = _a2.s, r = _a2.r;
      if (r.length)
        err(8);
      return s2;
    }
  }
  var slzh = function(d, b) {
    return b + 30 + b2(d, b + 26) + b2(d, b + 28);
  };
  var zh = function(d, b, z) {
    var fnl = b2(d, b + 28), fn = strFromU8(d.subarray(b + 46, b + 46 + fnl), !(b2(d, b + 8) & 2048)), es = b + 46 + fnl, bs = b4(d, b + 20);
    var _a2 = z && bs == 4294967295 ? z64e(d, es) : [bs, b4(d, b + 24), b4(d, b + 42)], sc = _a2[0], su = _a2[1], off = _a2[2];
    return [b2(d, b + 10), sc, su, fn, es + b2(d, b + 30) + b2(d, b + 32), off];
  };
  var z64e = function(d, b) {
    for (; b2(d, b) != 1; b += 4 + b2(d, b + 2))
      ;
    return [b8(d, b + 12), b8(d, b + 4), b8(d, b + 20)];
  };
  var exfl = function(ex) {
    var le = 0;
    if (ex) {
      for (var k in ex) {
        var l = ex[k].length;
        if (l > 65535)
          err(9);
        le += l + 4;
      }
    }
    return le;
  };
  var wzh = function(d, b, f, fn, u, c, ce, co) {
    var fl2 = fn.length, ex = f.extra, col = co && co.length;
    var exl = exfl(ex);
    wbytes(d, b, ce != null ? 33639248 : 67324752), b += 4;
    if (ce != null)
      d[b++] = 20, d[b++] = f.os;
    d[b] = 20, b += 2;
    d[b++] = f.flag << 1 | (c < 0 && 8), d[b++] = u && 8;
    d[b++] = f.compression & 255, d[b++] = f.compression >> 8;
    var dt = new Date(f.mtime == null ? Date.now() : f.mtime), y = dt.getFullYear() - 1980;
    if (y < 0 || y > 119)
      err(10);
    wbytes(d, b, y << 25 | dt.getMonth() + 1 << 21 | dt.getDate() << 16 | dt.getHours() << 11 | dt.getMinutes() << 5 | dt.getSeconds() >> 1), b += 4;
    if (c != -1) {
      wbytes(d, b, f.crc);
      wbytes(d, b + 4, c < 0 ? -c - 2 : c);
      wbytes(d, b + 8, f.size);
    }
    wbytes(d, b + 12, fl2);
    wbytes(d, b + 14, exl), b += 16;
    if (ce != null) {
      wbytes(d, b, col);
      wbytes(d, b + 6, f.attrs);
      wbytes(d, b + 10, ce), b += 14;
    }
    d.set(fn, b);
    b += fl2;
    if (exl) {
      for (var k in ex) {
        var exf = ex[k], l = exf.length;
        wbytes(d, b, +k);
        wbytes(d, b + 2, l);
        d.set(exf, b + 4), b += 4 + l;
      }
    }
    if (col)
      d.set(co, b), b += col;
    return b;
  };
  var wzf = function(o, b, c, d, e) {
    wbytes(o, b, 101010256);
    wbytes(o, b + 8, c);
    wbytes(o, b + 10, c);
    wbytes(o, b + 12, d);
    wbytes(o, b + 16, e);
  };
  function zipSync(data, opts) {
    if (!opts)
      opts = {};
    var r = {};
    var files = [];
    fltn(data, "", r, opts);
    var o = 0;
    var tot = 0;
    for (var fn in r) {
      var _a2 = r[fn], file = _a2[0], p = _a2[1];
      var compression = p.level == 0 ? 0 : 8;
      var f = strToU8(fn), s2 = f.length;
      var com = p.comment, m = com && strToU8(com), ms = m && m.length;
      var exl = exfl(p.extra);
      if (s2 > 65535)
        err(11);
      var d = compression ? deflateSync(file, p) : file, l = d.length;
      var c = crc();
      c.p(file);
      files.push(mrg(p, {
        size: file.length,
        crc: c.d(),
        c: d,
        f,
        m,
        u: s2 != fn.length || m && com.length != ms,
        o,
        compression
      }));
      o += 30 + s2 + exl + l;
      tot += 76 + 2 * (s2 + exl) + (ms || 0) + l;
    }
    var out = new u8(tot + 22), oe = o, cdl = tot - o;
    for (var i = 0; i < files.length; ++i) {
      var f = files[i];
      wzh(out, f.o, f, f.f, f.u, f.c.length);
      var badd = 30 + f.f.length + exfl(f.extra);
      out.set(f.c, f.o + badd);
      wzh(out, o, f, f.f, f.u, f.c.length, f.o, f.m), o += 16 + badd + (f.m ? f.m.length : 0);
    }
    wzf(out, o, files.length, cdl, oe);
    return out;
  }
  function unzipSync(data, opts) {
    var files = {};
    var e = data.length - 22;
    for (; b4(data, e) != 101010256; --e) {
      if (!e || data.length - e > 65558)
        err(13);
    }
    ;
    var c = b2(data, e + 8);
    if (!c)
      return {};
    var o = b4(data, e + 16);
    var z = o == 4294967295 || c == 65535;
    if (z) {
      var ze = b4(data, e - 12);
      z = b4(data, ze) == 101075792;
      if (z) {
        c = b4(data, ze + 32);
        o = b4(data, ze + 48);
      }
    }
    var fltr = opts && opts.filter;
    for (var i = 0; i < c; ++i) {
      var _a2 = zh(data, o, z), c_2 = _a2[0], sc = _a2[1], su = _a2[2], fn = _a2[3], no = _a2[4], off = _a2[5], b = slzh(data, off);
      o = no;
      if (!fltr || fltr({
        name: fn,
        size: sc,
        originalSize: su,
        compression: c_2
      })) {
        if (!c_2)
          files[fn] = slc(data, b, b + sc);
        else if (c_2 == 8)
          files[fn] = inflateSync(data.subarray(b, b + sc), { out: new u8(su) });
        else
          err(14, "unknown compression type " + c_2);
      }
    }
    return files;
  }

  // src/core.js
  var FORMAT = "resoarc.kintone.backup";
  var VERSION = 2;
  var MAX_BYTES = 25 * 1024 * 1024;
  var MAX_RECORDS = 2e4;
  var WRITABLE = /* @__PURE__ */ new Set(["SINGLE_LINE_TEXT", "MULTI_LINE_TEXT", "RICH_TEXT", "NUMBER", "RADIO_BUTTON", "DROP_DOWN", "CHECK_BOX", "MULTI_SELECT", "DATE", "TIME", "DATETIME", "LINK", "USER_SELECT", "ORGANIZATION_SELECT", "GROUP_SELECT", "FILE"]);
  var s = (v) => JSON.stringify(v);
  var u82 = (v) => v instanceof Uint8Array ? v : new Uint8Array(v);
  var stop = (reason) => {
    throw new Error(reason);
  };
  var sha256 = async (b) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", u82(b)))).map((v) => v.toString(16).padStart(2, "0")).join("");
  var allowedField = (d) => !!d && WRITABLE.has(d.type) && !d.lookup && !d.referenceTable && !(d.type === "SINGLE_LINE_TEXT" && typeof d.expression === "string" && d.expression.trim());
  var obj = (v) => v && typeof v === "object" && !Array.isArray(v);
  function fieldContents(props) {
    const fields = {};
    for (const [code2, def] of Object.entries(props || {})) {
      if (def?.type === "SUBTABLE") {
        const members = fieldContents(def.fields);
        if (Object.keys(members).length) fields[code2] = { type: "SUBTABLE", fields: members };
      } else if (allowedField(def)) fields[code2] = { type: def.type };
    }
    return fields;
  }
  var writableSchema = (raw) => fieldContents(raw?.properties || raw);
  function filterValue(value, def) {
    if (def.type === "SUBTABLE") {
      if (!Array.isArray(value)) return [];
      return value.map((row) => {
        const result = {};
        for (const [code2, fd2] of Object.entries(def.fields)) {
          if (row?.value?.[code2]) result[code2] = { value: filterValue(row.value[code2].value, fd2) };
        }
        return { value: result };
      });
    }
    if (def.type === "FILE") {
      return (Array.isArray(value) ? value : []).map((f) => ({ fileKey: String(f.fileKey || ""), name: String(f.name || ""), size: Number(f.size || 0), contentType: String(f.contentType || "application/octet-stream") }));
    }
    if (["USER_SELECT", "GROUP_SELECT", "ORGANIZATION_SELECT"].includes(def.type)) {
      return (Array.isArray(value) ? value : []).map((x) => ({ code: String(x.code) }));
    }
    if (Array.isArray(value)) return value.map((v) => obj(v) ? structuredClone(v) : v);
    return value === void 0 ? null : value;
  }
  function normalizeRecord(record, schema) {
    if (!obj(record) || !obj(schema)) stop("\u4E0D\u6B63\u306A\u30EC\u30B3\u30FC\u30C9\u5F62\u5F0F\u3067\u3059");
    const result = {};
    for (const [code2, def] of Object.entries(schema)) {
      if (record[code2]) result[code2] = { value: filterValue(record[code2].value, def) };
    }
    return result;
  }
  function visitFiles(rec, schema, visit) {
    for (const [code2, def] of Object.entries(schema)) {
      const val = rec[code2]?.value;
      if (def.type === "FILE" && Array.isArray(val)) {
        for (const f of val) visit(f);
      } else if (def.type === "SUBTABLE" && Array.isArray(val)) {
        for (const row of val) visitFiles(row.value, def.fields, visit);
      }
    }
  }
  var checkPath = (name) => {
    if (!/^(manifest\.json|schema\/(fields|layout|source-fields)\.json|data\/records\.jsonl|attachments\/[0-9a-f]{64})$/.test(name)) stop("ZIP\u5185\u306E\u4E0D\u6B63\u306A\u30D1\u30B9: " + name);
  };
  function sizeCheck(bytes, limit = MAX_BYTES) {
    if (bytes > limit) stop("\u5BB9\u91CF\u4E0A\u9650\uFF0825MiB\uFF09\u3092\u8D85\u3048\u307E\u3057\u305F\u3002\u5B89\u5168\u306E\u305F\u3081\u51E6\u7406\u3092\u4E2D\u6B62\u3057\u307E\u3059");
  }
  async function makeArchive({ appId, fields, layout, records, download, now = (/* @__PURE__ */ new Date()).toISOString(), maxBytes = MAX_BYTES }) {
    if (!Number.isSafeInteger(Number(appId)) || Number(appId) <= 0) stop("\u30A2\u30D7\u30EAID\u304C\u4E0D\u6B63\u3067\u3059");
    if (!Array.isArray(records) || records.length > MAX_RECORDS) stop("\u30EC\u30B3\u30FC\u30C9\u4E0A\u9650\u3092\u8D85\u3048\u307E\u3057\u305F");
    if (typeof download !== "function") stop("\u30D5\u30A1\u30A4\u30EB\u53D6\u5F97\u51E6\u7406\u304C\u5FC5\u8981\u3067\u3059");
    const schema = writableSchema(fields);
    const out = records.map((r) => normalizeRecord(r, schema));
    const contents = {};
    const attachments = {};
    let size = 0;
    for (const rec of out) {
      const pending = [];
      visitFiles(rec, schema, (f) => pending.push(f));
      for (const f of pending) {
        if (!f.fileKey) stop("\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u306E\u8B58\u5225\u5B50\u304C\u3042\u308A\u307E\u305B\u3093");
        sizeCheck(size + f.size, maxBytes);
        if (!attachments[f.fileKey]) {
          const bytes = u82(await download(f.fileKey));
          size += bytes.byteLength;
          sizeCheck(size, maxBytes);
          const hash = await sha256(bytes);
          contents["attachments/" + hash] = bytes;
          attachments[f.fileKey] = { ref: hash, name: f.name, size: bytes.byteLength, contentType: f.contentType };
        }
        const info = attachments[f.fileKey];
        f.ref = info.ref;
        f.name = info.name;
        f.size = info.size;
        f.contentType = info.contentType;
        delete f.fileKey;
      }
    }
    const texts = {
      "schema/fields.json": s(schema),
      "schema/layout.json": s(layout || {}),
      // Full source field definitions are only used to create a NEW app draft.
      // Never apply raw definitions to an existing app.
      "schema/source-fields.json": s({ properties: fields?.properties || fields || {} }),
      "data/records.jsonl": out.map((r) => s(r)).join("\n") + (out.length ? "\n" : "")
    };
    const digests = {};
    for (const [path, body] of Object.entries(texts)) {
      const bytes = strToU8(body);
      size += bytes.length;
      sizeCheck(size, maxBytes);
      contents[path] = bytes;
      digests[path] = await sha256(bytes);
    }
    const uniqueFiles = Object.entries(contents).filter(([name]) => name.startsWith("attachments/")).map(([path, b]) => ({ path, size: b.length, sha256: path.slice("attachments/".length) }));
    const manifest = {
      format: FORMAT,
      version: VERSION,
      createdAt: now,
      sourceAppId: Number(appId),
      recordCount: out.length,
      files: uniqueFiles,
      digests,
      limitations: ["append-only restore", "no system fields or audit history", "no process status reconstruction", "new-app draft only", "no permissions or views", "lookup values omitted"]
    };
    const manifestBytes = strToU8(s(manifest));
    size += manifestBytes.length;
    sizeCheck(size, maxBytes);
    contents["manifest.json"] = manifestBytes;
    const zip = zipSync(contents, { level: 6 });
    sizeCheck(zip.length, maxBytes);
    return { zip, manifest, hash: await sha256(zip) };
  }
  async function inspectArchive(zipInput, { expectedHash, maxBytes = MAX_BYTES } = {}) {
    const bytes = u82(zipInput);
    sizeCheck(bytes.byteLength, maxBytes);
    if (expectedHash && await sha256(bytes) !== expectedHash.toLowerCase()) stop("ZIP\u5168\u4F53\u306ESHA-256\u304C\u4E00\u81F4\u3057\u307E\u305B\u3093");
    let inflatedTotal = 0, entries;
    try {
      entries = unzipSync(bytes, { filter: (file) => {
        checkPath(file.name);
        const n = Number(file.originalSize);
        if (!Number.isSafeInteger(n) || n < 0) stop("ZIP\u306E\u30B5\u30A4\u30BA\u304C\u4E0D\u6B63\u3067\u3059");
        inflatedTotal += n;
        sizeCheck(inflatedTotal, maxBytes);
        return true;
      } });
    } catch (e) {
      throw new Error("ZIP\u5C55\u958B\u30FB\u691C\u8A3C\u306B\u5931\u6557\u3057\u307E\u3057\u305F: " + e.message);
    }
    const load = (path) => {
      if (!entries[path]) stop("\u5FC5\u9808\u30D5\u30A1\u30A4\u30EB\u304C\u3042\u308A\u307E\u305B\u3093: " + path);
      return strFromU8(entries[path]);
    };
    let manifest, schema, layout, sourceFields = null, records;
    try {
      manifest = JSON.parse(load("manifest.json"));
      schema = JSON.parse(load("schema/fields.json"));
      layout = JSON.parse(load("schema/layout.json"));
      const text = load("data/records.jsonl");
      records = text.trim() ? text.trimEnd().split("\n").map((line) => JSON.parse(line)) : [];
    } catch (e) {
      throw new Error("\u5185\u5BB9\u3092\u8AAD\u307F\u53D6\u308C\u307E\u305B\u3093: " + e.message);
    }
    if (manifest?.format !== FORMAT || ![1, 2].includes(manifest?.version)) stop("\u672A\u5BFE\u5FDC\u306E\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u5F62\u5F0F\u3067\u3059");
    const expectedTextPaths = ["schema/fields.json", "schema/layout.json", "data/records.jsonl"];
    if (manifest.version === 2) {
      try {
        sourceFields = JSON.parse(load("schema/source-fields.json"));
      } catch (e) {
        stop("v2\u5F62\u5F0F\u306E\u30D5\u30A9\u30FC\u30E0\u5B9A\u7FA9\u304C\u4E0D\u6B63\u3067\u3059: " + e.message);
      }
      if (!obj(sourceFields) || !obj(sourceFields.properties)) stop("\u30D5\u30A9\u30FC\u30E0\u5B9A\u7FA9\u304C\u4E0D\u6B63\u3067\u3059");
      expectedTextPaths.push("schema/source-fields.json");
    }
    if (manifest.version === 1 && entries["schema/source-fields.json"]) stop("v1\u5F62\u5F0F\u306B\u672A\u691C\u8A3C\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u8A2D\u5B9A\u304C\u3042\u308A\u307E\u3059");
    if (!obj(schema) || !Array.isArray(records) || records.length > MAX_RECORDS || records.length !== manifest.recordCount) stop("\u4EF6\u6570\u307E\u305F\u306F\u30D5\u30A3\u30FC\u30EB\u30C9\u69CB\u9020\u304C\u4E0D\u6B63\u3067\u3059");
    for (const p of expectedTextPaths) {
      if (await sha256(entries[p]) !== manifest.digests?.[p]) stop("\u5185\u5BB9\u306E\u30CF\u30C3\u30B7\u30E5\u304C\u4E00\u81F4\u3057\u307E\u305B\u3093: " + p);
    }
    if (sourceFields && JSON.stringify(writableSchema(sourceFields)) !== JSON.stringify(schema))
      stop("\u30EC\u30B3\u30FC\u30C9\u69CB\u9020\u3068\u5143\u30A2\u30D7\u30EA\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u5B9A\u7FA9\u304C\u77DB\u76FE\u3057\u3066\u3044\u307E\u3059");
    if (!Array.isArray(manifest.files)) stop("\u30D5\u30A1\u30A4\u30EB\u4E00\u89A7\u304C\u4E0D\u6B63\u3067\u3059");
    const manifestPaths = /* @__PURE__ */ new Set();
    for (const f of manifest.files) {
      if (!f || typeof f.path !== "string" || !/^attachments\/[0-9a-f]{64}$/.test(f.path) || manifestPaths.has(f.path)) stop("\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u4E00\u89A7\u304C\u4E0D\u6B63\u3067\u3059");
      manifestPaths.add(f.path);
      if (!entries[f.path] || entries[f.path].length !== f.size || await sha256(entries[f.path]) !== f.sha256 || f.path !== "attachments/" + f.sha256) stop("\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u306E\u6574\u5408\u6027\u30A8\u30E9\u30FC");
    }
    for (const p of Object.keys(entries)) {
      checkPath(p);
      if (p.startsWith("attachments/") && !manifestPaths.has(p)) stop("\u672A\u7533\u544A\u306E\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u304C\u3042\u308A\u307E\u3059");
    }
    for (const r of records) {
      if (!obj(r)) stop("\u30EC\u30B3\u30FC\u30C9\u304C\u4E0D\u6B63\u3067\u3059");
      visitFiles(r, schema, (f) => {
        if (!manifestPaths.has("attachments/" + f.ref)) stop("\u30EC\u30B3\u30FC\u30C9\u304C\u53C2\u7167\u3059\u308B\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u304C\u6B20\u843D\u3057\u3066\u3044\u307E\u3059");
      });
    }
    return { manifest, schema, layout, sourceFields, records, files: entries, archiveHash: await sha256(bytes) };
  }
  function createRestorePlan(archive, targetFields, targetAppId, managementAppId) {
    if (!archive?.manifest || !obj(archive.schema) || !Array.isArray(archive.records)) stop("\u691C\u8A3C\u6E08\u307F\u30A2\u30FC\u30AB\u30A4\u30D6\u304C\u5FC5\u8981\u3067\u3059");
    const id = Number(targetAppId);
    if (!Number.isSafeInteger(id) || id <= 0 || id === Number(managementAppId)) stop("\u5FA9\u5143\u5148\u30A2\u30D7\u30EAID\u304C\u4E0D\u6B63\u307E\u305F\u306F\u7BA1\u7406\u30A2\u30D7\u30EA\u3067\u3059");
    const target = writableSchema(targetFields);
    const mapped = {}, skipped = [];
    for (const [code2, def] of Object.entries(archive.schema)) {
      const t = target[code2];
      if (!t) {
        skipped.push(code2 + ": \u5FA9\u5143\u5148\u306B\u5B58\u5728\u3057\u307E\u305B\u3093");
        continue;
      }
      if (t.type !== def.type) stop("\u4E92\u63DB\u6027\u306E\u306A\u3044\u30D5\u30A3\u30FC\u30EB\u30C9\u578B: " + code2 + " (" + def.type + " -> " + t.type + ")");
      if (def.type === "SUBTABLE") {
        const members = {};
        for (const [sub, sd] of Object.entries(def.fields)) {
          if (!t.fields[sub]) {
            skipped.push(code2 + "." + sub + ": \u5FA9\u5143\u5148\u306B\u5B58\u5728\u3057\u307E\u305B\u3093");
            continue;
          }
          if (t.fields[sub].type !== sd.type) stop("\u30C6\u30FC\u30D6\u30EB\u5185\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u578B\u304C\u4E00\u81F4\u3057\u307E\u305B\u3093: " + code2 + "." + sub);
          members[sub] = sd;
        }
        mapped[code2] = { type: "SUBTABLE", fields: members };
      } else mapped[code2] = def;
    }
    const copyMapped = (r, defs) => {
      const targetRecord = {};
      for (const [code2, def] of Object.entries(defs)) {
        if (!r[code2]) continue;
        if (def.type === "SUBTABLE") {
          targetRecord[code2] = { value: (r[code2].value || []).map((row) => ({ value: copyMapped(row.value || {}, def.fields) })) };
        } else targetRecord[code2] = { value: structuredClone(r[code2].value) };
      }
      return targetRecord;
    };
    const rows = archive.records.map((r) => copyMapped(r, mapped));
    if (rows.length && Object.keys(mapped).length === 0) stop("\u8EE2\u9001\u3067\u304D\u308B\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u3042\u308A\u307E\u305B\u3093");
    const fileRefs = new Set(archive.manifest.files.map((f) => f.sha256));
    for (const r of rows) visitFiles(r, mapped, (f) => {
      if (!fileRefs.has(f.ref)) stop("\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u53C2\u7167\u304C\u4E0D\u6B63\u3067\u3059");
    });
    return { targetAppId: id, rows, mapped, skipped, recordCount: rows.length, sourceAppId: archive.manifest.sourceAppId, archiveCreatedAt: archive.manifest.createdAt };
  }
  async function materializeRestoreRow(row, schema, upload, entries) {
    const out = structuredClone(row);
    const todo = [];
    visitFiles(out, schema, (f) => todo.push(f));
    for (const f of todo) {
      const bytes = entries["attachments/" + f.ref];
      if (!bytes) stop("\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u306E\u5B9F\u4F53\u304C\u3042\u308A\u307E\u305B\u3093");
      const key = await upload(bytes, f.name || "file.bin", f.contentType || "application/octet-stream");
      delete f.ref;
      delete f.name;
      delete f.size;
      delete f.contentType;
      f.fileKey = key;
    }
    return out;
  }

  // src/restore.js
  var MARKER_CODE = "ResoArcRestoreKey";
  var bad = (message) => {
    throw new Error(message);
  };
  var object = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
  var unsafe = /* @__PURE__ */ new Set(["__proto__", "prototype", "constructor"]);
  var code = (v) => typeof v === "string" && v.length > 0 && v.length <= 128 && !unsafe.has(v) && !/[/\\\[\].\s]/u.test(v);
  var ensureCode = (v) => {
    if (!code(v)) bad("\u4E0D\u6B63\u306A\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9: " + String(v));
    return v;
  };
  var put = (obj2, key, value) => Object.defineProperty(obj2, key, { value, writable: true, enumerable: true, configurable: true });
  var own = (obj2, key) => Object.hasOwn(obj2, key);
  function createMappedRestorePlan(archive, targetFields, targetAppId, managementAppId, mapping = {}) {
    if (!object(mapping)) bad("\u30D5\u30A3\u30FC\u30EB\u30C9\u5BFE\u5FDC\u8868\u306FJSON\u30AA\u30D6\u30B8\u30A7\u30AF\u30C8\u306B\u3057\u3066\u304F\u3060\u3055\u3044");
    if (!archive?.schema || !Array.isArray(archive?.records)) bad("\u691C\u8A3C\u6E08\u307F\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u304C\u5FC5\u8981\u3067\u3059");
    const src = archive.schema, usedTargets = /* @__PURE__ */ new Set();
    const target = targetFields?.properties || targetFields;
    if (!object(target)) bad("\u79FB\u884C\u5148\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u8A2D\u5B9A\u304C\u3042\u308A\u307E\u305B\u3093");
    const sourcePaths = /* @__PURE__ */ new Set();
    for (const [name, def] of Object.entries(src)) {
      sourcePaths.add(name);
      if (def.type === "SUBTABLE") for (const child of Object.keys(def.fields || {})) sourcePaths.add(name + "." + child);
    }
    for (const [from, to] of Object.entries(mapping)) {
      if (!sourcePaths.has(from)) bad("\u5BFE\u5FDC\u8868\u306B\u5B58\u5728\u3057\u306A\u3044\u5143\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u3042\u308A\u307E\u3059: " + from);
      if (typeof to !== "string") bad("\u79FB\u884C\u5148\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9\u306F\u6587\u5B57\u5217\u3067\u6307\u5B9A\u3057\u3066\u304F\u3060\u3055\u3044: " + from);
      for (const p of to.split(".")) ensureCode(p);
      if (from.split(".").length !== to.split(".").length) bad("\u30C6\u30FC\u30D6\u30EB\u968E\u5C64\u304C\u4E00\u81F4\u3057\u307E\u305B\u3093: " + from);
      if (to.split(".").length > 2) bad("\u30C6\u30FC\u30D6\u30EB\u306E\u5165\u308C\u5B50\u306F\u672A\u5BFE\u5FDC\u3067\u3059");
      if (to === MARKER_CODE || to.endsWith("." + MARKER_CODE)) bad("\u5FA9\u5143\u7BA1\u7406\u7528\u30D5\u30A3\u30FC\u30EB\u30C9\u306F\u5BFE\u5FDC\u5148\u306B\u6307\u5B9A\u3067\u304D\u307E\u305B\u3093");
    }
    const renamedSchema = /* @__PURE__ */ Object.create(null);
    const schemaCopy = (defs, mappedDefs, tableSource = "", tableTarget = "") => {
      for (const [name, def] of Object.entries(defs)) {
        if (!tableSource && name === MARKER_CODE) continue;
        const from = tableSource ? tableSource + "." + name : name;
        const destName = own(mapping, from) ? mapping[from] : tableTarget ? tableTarget + "." + name : name;
        const destParts = destName.split(".");
        const expectedDepth = tableSource ? 2 : 1;
        if (destParts.length !== expectedDepth) bad("\u30D5\u30A3\u30FC\u30EB\u30C9\u5BFE\u5FDC\u306E\u968E\u5C64\u304C\u4E0D\u6B63\u3067\u3059: " + from);
        destParts.forEach(ensureCode);
        if (tableSource && destParts[0] !== tableTarget) bad("\u30C6\u30FC\u30D6\u30EB\u5185\u30D5\u30A3\u30FC\u30EB\u30C9\u306E\u5BFE\u5FDC\u5148\u304C\u89AA\u30C6\u30FC\u30D6\u30EB\u3068\u7570\u306A\u308A\u307E\u3059: " + from);
        const destField = destParts.at(-1);
        if (!tableSource && destField === MARKER_CODE) bad("\u5FA9\u5143\u7BA1\u7406\u7528\u30D5\u30A3\u30FC\u30EB\u30C9\u3092\u4E0A\u66F8\u304D\u3067\u304D\u307E\u305B\u3093");
        const complete = tableSource ? destParts.join(".") : destField;
        if (usedTargets.has(complete)) bad("\u8907\u6570\u306E\u5143\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u540C\u3058\u79FB\u884C\u5148\u3092\u53C2\u7167\u3057\u3066\u3044\u307E\u3059: " + complete);
        usedTargets.add(complete);
        if (def.type === "SUBTABLE") {
          const nestedSchema = /* @__PURE__ */ Object.create(null);
          schemaCopy(def.fields, nestedSchema, name, destField);
          put(mappedDefs, destField, { type: "SUBTABLE", fields: nestedSchema });
        } else put(mappedDefs, destField, { type: def.type });
      }
    };
    schemaCopy(src, renamedSchema);
    const remapRow = (defs, row, tableSource = "", tableTarget = "") => {
      const out = /* @__PURE__ */ Object.create(null);
      for (const [name, def] of Object.entries(defs)) {
        if (!tableSource && name === MARKER_CODE) continue;
        if (!own(row || {}, name)) continue;
        const from = tableSource ? tableSource + "." + name : name;
        const targetPath = own(mapping, from) ? mapping[from] : tableTarget ? tableTarget + "." + name : name;
        const dest = targetPath.split(".").at(-1);
        if (def.type === "SUBTABLE") {
          put(out, dest, { value: (row[name].value || []).map((r) => ({ value: remapRow(def.fields, r.value, name, dest) })) });
        } else put(out, dest, { value: structuredClone(row[name].value) });
      }
      return out;
    };
    const rows = archive.records.map((r) => remapRow(src, r));
    const mappedArchive = { ...archive, schema: renamedSchema, records: rows };
    const plan = createRestorePlan(mappedArchive, targetFields, targetAppId, managementAppId);
    plan.mapping = structuredClone(mapping);
    for (const [from, to] of Object.entries(mapping)) {
      const targetParts = to.split(".");
      const schemaEntry = targetParts.length === 1 ? target[targetParts[0]] : target[targetParts[0]]?.fields?.[targetParts[1]];
      if (!schemaEntry) bad("\u5BFE\u5FDC\u8868\u306E\u79FB\u884C\u5148\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u5B58\u5728\u3057\u307E\u305B\u3093: " + to);
      if (plan.skipped.some((x) => x === to + ": \u5FA9\u5143\u5148\u306B\u5B58\u5728\u3057\u307E\u305B\u3093")) bad("\u5BFE\u5FDC\u5148\u3092\u79FB\u884C\u3067\u304D\u307E\u305B\u3093: " + to);
    }
    const validChoices = /* @__PURE__ */ new Set(["DROP_DOWN", "RADIO_BUTTON", "CHECK_BOX", "MULTI_SELECT"]);
    const checkRow = (row, defs, fieldDefs, location) => {
      for (const [field, info] of Object.entries(defs)) {
        const dest = fieldDefs?.[field];
        if (!dest) continue;
        const value = row[field]?.value;
        if (info.type === "SUBTABLE") {
          for (const [index, sub] of (Array.isArray(value) ? value : []).entries())
            checkRow(sub.value || {}, info.fields, dest.fields, location + field + "[" + index + "].");
        } else if (validChoices.has(info.type) && value !== void 0 && value !== null) {
          const choices = new Set(Object.keys(dest.options || {}));
          const chosen = Array.isArray(value) ? value : [value];
          for (const selected of chosen) {
            if (selected !== "" && selected !== null && !choices.has(String(selected)))
              bad("\u79FB\u884C\u5148\u306E\u9078\u629E\u80A2\u306B\u5B58\u5728\u3057\u306A\u3044\u5024: " + location + field + " = " + String(selected));
          }
        }
      }
    };
    for (const [index, row] of plan.rows.entries()) checkRow(row, plan.mapped, target, "record[" + index + "].");
    for (const [name, definition2] of Object.entries(target)) {
      if (name === MARKER_CODE) continue;
      if (definition2.required === true && !own(plan.mapped, name) && (definition2.defaultValue === void 0 || definition2.defaultValue === null || definition2.defaultValue === ""))
        bad("\u5FA9\u5143\u5148\u306B\u672A\u5BFE\u5FDC\u306E\u5FC5\u9808\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u3042\u308A\u307E\u3059: " + name);
    }
    const marker = target[MARKER_CODE];
    if (!marker || marker.type !== "SINGLE_LINE_TEXT" || marker.unique !== true || marker.lookup || marker.expression)
      bad("\u79FB\u884C\u5148\u306B\u91CD\u8907\u7981\u6B62\u306E\u6587\u5B57\u5217\uFF081\u884C\uFF09\u30D5\u30A3\u30FC\u30EB\u30C9 " + MARKER_CODE + " \u304C\u5FC5\u8981\u3067\u3059\u3002\u65E2\u5B58\u30A2\u30D7\u30EA\u306E\u5834\u5408\u306F\u7BA1\u7406\u8005\u304C\u8FFD\u52A0\u3057\u3066\u304F\u3060\u3055\u3044");
    if (plan.rows.some((row) => own(row, MARKER_CODE))) bad("\u5FA9\u5143\u7BA1\u7406\u7528\u30D5\u30A3\u30FC\u30EB\u30C9\u306F\u30C7\u30FC\u30BF\u306B\u542B\u3081\u3089\u308C\u307E\u305B\u3093");
    plan.markerCode = MARKER_CODE;
    return plan;
  }
  function digestUtf8(s2) {
    return sha256(new TextEncoder().encode(s2));
  }
  async function restoreKeyBase(archive, plan) {
    if (!/^[0-9a-f]{64}$/.test(archive?.archiveHash || "")) bad("\u691C\u8A3C\u6E08\u307F\u30A2\u30FC\u30AB\u30A4\u30D6\u306E\u30CF\u30C3\u30B7\u30E5\u304C\u5FC5\u8981\u3067\u3059");
    const canonicalMapping = Object.fromEntries(Object.entries(plan.mapping || {}).sort(([a], [b]) => a.localeCompare(b, "en")));
    const mapDigest = await digestUtf8(JSON.stringify(canonicalMapping));
    const base = "RA3_" + archive.archiveHash.slice(0, 32) + "_" + mapDigest.slice(0, 12) + "_";
    return { base, archivePrefix: "RA3_" + archive.archiveHash.slice(0, 32) + "_", mappingFingerprint: mapDigest.slice(0, 12) };
  }
  function keyForIndex(base, index) {
    if (!Number.isSafeInteger(index) || index < 0) bad("\u5FA9\u5143\u884C\u756A\u53F7\u304C\u4E0D\u6B63\u3067\u3059");
    const key = base + index.toString(36);
    if (key.length > 64) bad("\u5FA9\u5143\u8B58\u5225\u5B50\u304C\u9577\u3059\u304E\u307E\u3059");
    return key;
  }
  async function scanRestoreKeys(app, api2, { maxRows = 2e5 } = {}) {
    const response = await api2("/k/v1/records/cursor.json", "POST", { app, fields: [MARKER_CODE], size: 500 });
    if (!response?.id) bad("\u5FA9\u5143\u6E08\u307F\u78BA\u8A8D\u7528\u306ECursor\u3092\u4F5C\u6210\u3067\u304D\u307E\u305B\u3093\u3067\u3057\u305F");
    let finished = false, count = 0;
    const keys = /* @__PURE__ */ new Set();
    try {
      while (!finished) {
        const page = await api2("/k/v1/records/cursor.json", "GET", { id: response.id });
        if (!Array.isArray(page?.records)) bad("\u79FB\u884C\u5148\u306E\u53D6\u5F97\u7D50\u679C\u304C\u4E0D\u6B63\u3067\u3059");
        count += page.records.length;
        if (count > maxRows) bad("\u79FB\u884C\u5148\u306E\u30EC\u30B3\u30FC\u30C9\u6570\u304C\u691C\u7D22\u4E0A\u9650\u3092\u8D85\u3048\u3066\u3044\u307E\u3059");
        for (const record of page.records) {
          const k = record?.[MARKER_CODE]?.value;
          if (typeof k === "string" && k) keys.add(k);
        }
        finished = !page.next;
      }
    } finally {
      if (!finished) try {
        await api2("/k/v1/records/cursor.json", "DELETE", { id: response.id });
      } catch {
      }
    }
    return keys;
  }
  async function previewRestoreProgress({ archive, plan, api: api2 }) {
    if (plan?.markerCode !== MARKER_CODE || !Array.isArray(plan?.rows)) bad("\u5FA9\u5143\u7528\u30D7\u30E9\u30F3\u304C\u4E0D\u6B63\u3067\u3059");
    const { base, archivePrefix } = await restoreKeyBase(archive, plan);
    const keys = await scanRestoreKeys(plan.targetAppId, api2);
    if ([...keys].some((k) => k.startsWith(archivePrefix) && !k.startsWith(base)))
      bad("\u540C\u3058\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u3092\u5225\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u5BFE\u5FDC\u4ED8\u3051\u3067\u79FB\u884C\u3057\u305F\u5C65\u6B74\u304C\u3042\u308A\u307E\u3059\u3002\u30C7\u30FC\u30BF\u3092\u78BA\u8A8D\u3057\u3066\u304F\u3060\u3055\u3044");
    const missingIndexes = [];
    for (let i = 0; i < plan.rows.length; i++) if (!keys.has(keyForIndex(base, i))) missingIndexes.push(i);
    return { base, missingIndexes, total: plan.rows.length, already: plan.rows.length - missingIndexes.length, remaining: missingIndexes.length };
  }
  async function runResumableRestore({ archive, plan, api: api2, upload, onProgress = () => {
  }, batchSize = 20 }) {
    if (typeof api2 !== "function" || typeof upload !== "function") bad("kintone API\u306E\u5B9F\u88C5\u304C\u5FC5\u8981\u3067\u3059");
    if (!Number.isSafeInteger(batchSize) || batchSize < 1 || batchSize > 100) bad("\u30D0\u30C3\u30C1\u4EF6\u6570\u304C\u4E0D\u6B63\u3067\u3059");
    if (plan?.markerCode !== MARKER_CODE || !Array.isArray(plan?.rows)) bad("\u5FA9\u5143\u7528\u30D7\u30E9\u30F3\u304C\u4E0D\u6B63\u3067\u3059");
    const snapshot = await previewRestoreProgress({ archive, plan, api: api2 });
    const { base } = snapshot;
    const missing = snapshot.missingIndexes;
    onProgress({ total: plan.rows.length, already: snapshot.already, added: 0, remaining: missing.length });
    let completed = 0;
    for (let start = 0; start < missing.length; start += batchSize) {
      const indexes = missing.slice(start, start + batchSize);
      const records = [];
      for (const index of indexes) {
        const row = await materializeRestoreRow(plan.rows[index], plan.mapped, upload, archive.files);
        row[MARKER_CODE] = { value: keyForIndex(base, index) };
        records.push(row);
      }
      const result = await api2("/k/v1/records.json", "POST", { app: plan.targetAppId, records });
      if (!Array.isArray(result?.ids) || result.ids.length !== records.length)
        bad("\u767B\u9332\u7D50\u679C\u3092\u78BA\u8A8D\u3067\u304D\u307E\u305B\u3093\u3002\u5FA9\u5143\u5148\u3092\u518D\u78BA\u8A8D\u3057\u3066\u304B\u3089\u518D\u958B\u3057\u3066\u304F\u3060\u3055\u3044");
      completed += records.length;
      onProgress({ total: plan.rows.length, already: plan.rows.length - missing.length, added: completed, remaining: missing.length - completed });
    }
    return { total: plan.rows.length, added: completed, already: plan.rows.length - missing.length, completed: true };
  }

  // src/migration.js
  var TYPES = /* @__PURE__ */ new Set([
    "SINGLE_LINE_TEXT",
    "MULTI_LINE_TEXT",
    "RICH_TEXT",
    "NUMBER",
    "RADIO_BUTTON",
    "DROP_DOWN",
    "CHECK_BOX",
    "MULTI_SELECT",
    "DATE",
    "TIME",
    "DATETIME",
    "LINK",
    "USER_SELECT",
    "ORGANIZATION_SELECT",
    "GROUP_SELECT",
    "FILE"
  ]);
  var SELECT = /* @__PURE__ */ new Set(["RADIO_BUTTON", "DROP_DOWN", "CHECK_BOX", "MULTI_SELECT"]);
  var TABLE_TYPES = new Set([...TYPES].filter((t) => t !== "RICH_TEXT"));
  var SAFE_CODE = /^[^\s.\[\]\\/]{1,128}$/u;
  var bad2 = (message) => {
    throw new Error(message);
  };
  var plain = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
  var str = (x) => typeof x === "string" ? x : "";
  var copy = (o, keys, into) => {
    for (const key of keys) if (Object.hasOwn(o, key)) into[key] = structuredClone(o[key]);
  };
  function definition(code2, raw, inTable, skipped) {
    if (!plain(raw) || !SAFE_CODE.test(code2) || ["__proto__", "prototype", "constructor"].includes(code2)) {
      skipped.push(code2 + ": \u672A\u5BFE\u5FDC\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9");
      return null;
    }
    if (raw.type === "SUBTABLE") {
      if (inTable) {
        skipped.push(code2 + ": \u30C6\u30FC\u30D6\u30EB\u306E\u5165\u308C\u5B50\u306F\u672A\u5BFE\u5FDC");
        return null;
      }
      const fields = {};
      for (const [child, def2] of Object.entries(raw.fields || {})) {
        const built = definition(child, def2, true, skipped);
        if (built) Object.defineProperty(fields, child, { value: built, enumerable: true, writable: true, configurable: true });
      }
      if (!Object.keys(fields).length) {
        skipped.push(code2 + ": \u30C6\u30FC\u30D6\u30EB\u5185\u306E\u79FB\u884C\u53EF\u80FD\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u3042\u308A\u307E\u305B\u3093");
        return null;
      }
      return { type: "SUBTABLE", code: code2, label: str(raw.label) || code2, fields };
    }
    if (!TYPES.has(raw.type) || raw.lookup || raw.referenceTable || inTable && !TABLE_TYPES.has(raw.type)) {
      skipped.push(code2 + ": \u5BFE\u5FDC\u3067\u304D\u306A\u3044\u30D5\u30A3\u30FC\u30EB\u30C9\u7A2E\u5225\u307E\u305F\u306F\u53C2\u7167\u8A2D\u5B9A (" + (raw.type || "unknown") + ")");
      return null;
    }
    const def = { type: raw.type, code: code2, label: str(raw.label) || code2, required: false, unique: false };
    if (SELECT.has(raw.type)) {
      if (!plain(raw.options) || Object.keys(raw.options).length === 0) {
        skipped.push(code2 + ": \u9078\u629E\u80A2\u304C\u306A\u304F\u518D\u4F5C\u6210\u3067\u304D\u307E\u305B\u3093");
        return null;
      }
      const options = {};
      for (const [label, opt] of Object.entries(raw.options)) {
        if (!plain(opt) || !label || !Number.isFinite(Number(opt.index))) {
          skipped.push(code2 + ": \u9078\u629E\u80A2\u8A2D\u5B9A\u304C\u4E0D\u6B63\u3067\u3059");
          return null;
        }
        Object.defineProperty(options, label, { value: { label, index: String(opt.index) }, enumerable: true, writable: true, configurable: true });
      }
      def.options = options;
      if (raw.type === "RADIO_BUTTON" || raw.type === "CHECK_BOX" || raw.type === "MULTI_SELECT") {
        if (["VERTICAL", "HORIZONTAL"].includes(raw.align)) def.align = raw.align;
      }
    }
    if (raw.type === "LINK") def.protocol = ["WEB", "CALL", "MAIL"].includes(raw.protocol) ? raw.protocol : "WEB";
    if (raw.type === "NUMBER") copy(raw, ["digit", "displayScale", "unit", "unitPosition"], def);
    if (raw.type === "FILE" && ["50", "150", "250", "500"].includes(String(raw.thumbnailSize))) def.thumbnailSize = String(raw.thumbnailSize);
    return def;
  }
  function planNewApp(archive, name) {
    if (!archive || !archive.manifest || !plain(archive.sourceFields?.properties))
      bad2("\u3053\u306E\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u306B\u306F\u30A2\u30D7\u30EA\u69CB\u9020\u518D\u73FE\u7528\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u8A2D\u5B9A\u304C\u3042\u308A\u307E\u305B\u3093\u3002v2\u5F62\u5F0F\u3067\u518D\u53D6\u5F97\u3057\u3066\u304F\u3060\u3055\u3044");
    if (archive.manifest.version !== 2) bad2("\u81EA\u52D5\u30D5\u30A9\u30FC\u30E0\u518D\u73FE\u306Fv2\u5F62\u5F0F\u3060\u3051\u5BFE\u5FDC\u3057\u307E\u3059");
    if (typeof name !== "string" || !name.trim() || name.length > 64) bad2("\u30A2\u30D7\u30EA\u540D\u306F1\uFF5E64\u6587\u5B57\u306B\u3057\u3066\u304F\u3060\u3055\u3044");
    const props = {};
    const skipped = [];
    for (const [code2, def] of Object.entries(archive.sourceFields.properties)) {
      const compiled = definition(code2, def, false, skipped);
      if (compiled) Object.defineProperty(props, code2, { value: compiled, enumerable: true, writable: true, configurable: true });
    }
    if (!Object.keys(props).length) bad2("\u79FB\u884C\u3067\u304D\u308B\u30D5\u30A3\u30FC\u30EB\u30C9\u304C\u3042\u308A\u307E\u305B\u3093");
    Object.defineProperty(props, "ResoArcRestoreKey", { value: {
      type: "SINGLE_LINE_TEXT",
      code: "ResoArcRestoreKey",
      label: "ResoArc\u5FA9\u5143\u8B58\u5225\u5B50",
      required: false,
      unique: true
    }, writable: true, enumerable: true, configurable: true });
    const sourceCodes = Object.keys(archive.schema);
    const missing = sourceCodes.filter((code2) => !Object.hasOwn(props, code2));
    for (const code2 of missing) if (!skipped.some((s2) => s2.startsWith(code2 + ":"))) skipped.push(code2 + ": \u79FB\u884C\u5BFE\u8C61\u304B\u3089\u9664\u5916");
    return {
      name: name.trim(),
      properties: props,
      skipped,
      fieldCount: Object.keys(props).length,
      sourceAppId: archive.manifest.sourceAppId,
      recordCount: archive.records.length,
      warnings: ["\u65E2\u5B58\u306E\u30A2\u30D7\u30EA\u306B\u306F\u9069\u7528\u3057\u307E\u305B\u3093", "\u5143\u306E\u8868\u793A\u914D\u7F6E\u30FB\u6A29\u9650\u30FB\u4E00\u89A7\u30FB\u30D7\u30ED\u30BB\u30B9\u30FB\u30EB\u30C3\u30AF\u30A2\u30C3\u30D7\u53C2\u7167\u306F\u518D\u73FE\u3057\u307E\u305B\u3093", "\u5FC5\u9808\u30FB\u4E00\u610F\u5236\u7D04\u306F\u79FB\u884C\u512A\u5148\u306E\u305F\u3081\u7121\u52B9\u306B\u3057\u307E\u3059", "\u30C7\u30FC\u30BF\u5FA9\u5143\u306F\u5225\u9014\u30D7\u30EC\u30D3\u30E5\u30FC\u3068\u660E\u793A\u627F\u8A8D\u304C\u5FC5\u8981\u3067\u3059"]
    };
  }
  async function createDraftApp(plan, api2, onStep = () => {
  }) {
    if (typeof api2 !== "function") bad2("kintone API\u95A2\u6570\u304C\u3042\u308A\u307E\u305B\u3093");
    if (!plan?.name || !plain(plan.properties) || !Object.keys(plan.properties).length) bad2("\u4F5C\u6210\u8A08\u753B\u304C\u4E0D\u6B63\u3067\u3059");
    onStep("\u52D5\u4F5C\u30C6\u30B9\u30C8\u74B0\u5883\u306B\u65B0\u898F\u30A2\u30D7\u30EA\u3092\u4F5C\u6210\u3057\u3066\u3044\u307E\u3059");
    const created = await api2("/k/v1/preview/app.json", "POST", { name: plan.name });
    const id = Number(created?.app);
    if (!Number.isSafeInteger(id) || id <= 0) bad2("\u65B0\u898F\u30A2\u30D7\u30EAID\u3092\u53D6\u5F97\u3067\u304D\u307E\u305B\u3093\u3067\u3057\u305F");
    try {
      onStep("\u65B0\u898F\u30A2\u30D7\u30EA #" + id + " \u306B\u30D5\u30A3\u30FC\u30EB\u30C9\u3092\u8A2D\u5B9A\u3057\u3066\u3044\u307E\u3059");
      await api2("/k/v1/preview/app/form/fields.json", "POST", { app: id, properties: plan.properties });
      onStep("\u65B0\u898F\u30A2\u30D7\u30EA #" + id + " \u306E\u4E0B\u66F8\u304D\u304C\u3067\u304D\u307E\u3057\u305F\u3002\u30A2\u30D7\u30EA\u306E\u8A2D\u5B9A\u753B\u9762\u3067\u5185\u5BB9\u3092\u78BA\u8A8D\u3057\u3066\u304F\u3060\u3055\u3044");
    } catch (e) {
      throw new Error("\u30A2\u30D7\u30EA #" + id + " \u306F\u4F5C\u6210\u3055\u308C\u307E\u3057\u305F\u304C\u3001\u30D5\u30A3\u30FC\u30EB\u30C9\u8FFD\u52A0\u304C\u5931\u6557\u3057\u307E\u3057\u305F\u3002\u8A2D\u5B9A\u753B\u9762\u3067\u78BA\u8A8D\u3057\u3066\u304F\u3060\u3055\u3044\u3002\u539F\u56E0: " + e.message);
    }
    return { appId: id, deployed: false, recordsCopied: 0, requiresManualDeploy: true };
  }

  // src/browser.js
  var K = window.kintone;
  var api = (path, method, body) => K.api(K.api.url(path, true), method, body);
  var positiveId = (v) => {
    const n = Number(v);
    if (!Number.isSafeInteger(n) || n <= 0) throw Error("\u30A2\u30D7\u30EA\u30FB\u30EC\u30B3\u30FC\u30C9ID\u306F\u6B63\u306E\u6574\u6570\u3067\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044");
    return n;
  };
  function managementApp() {
    const id = Number(K.app.getId());
    if (!id) throw Error("kintone\u30A2\u30D7\u30EA\u306E\u4E00\u89A7\u753B\u9762\u304B\u3089\u5B9F\u884C\u3057\u3066\u304F\u3060\u3055\u3044");
    return id;
  }
  function ensureExternalId(id) {
    if (id === managementApp()) throw Error("\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u7BA1\u7406\u30A2\u30D7\u30EA\u81EA\u4F53\u306F\u5BFE\u8C61\u306B\u3067\u304D\u307E\u305B\u3093");
  }
  var getFields = (app) => api("/k/v1/app/form/fields.json", "GET", { app });
  var getLayout = (app) => api("/k/v1/app/form/layout.json", "GET", { app });
  async function listRecords(app) {
    const created = await api("/k/v1/records/cursor.json", "POST", { app, size: 500 });
    let cursor = created.id, done = false;
    const records = [];
    try {
      while (!done) {
        const page = await api("/k/v1/records/cursor.json", "GET", { id: cursor });
        records.push(...page.records);
        if (records.length > 2e4) throw Error("\u4E00\u5EA6\u306B\u51E6\u7406\u3067\u304D\u308B\u30EC\u30B3\u30FC\u30C9\u306F20,000\u4EF6\u307E\u3067\u3067\u3059");
        done = !page.next;
      }
    } finally {
      if (!done) try {
        await api("/k/v1/records/cursor.json", "DELETE", { id: cursor });
      } catch (e) {
        console.warn("cursor cleanup failed", e);
      }
    }
    return records;
  }
  async function downloadFile(fileKey) {
    const resp = await fetch("/k/v1/file.json?fileKey=" + encodeURIComponent(fileKey), { method: "GET", headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!resp.ok) throw Error("\u30D5\u30A1\u30A4\u30EB\u306E\u53D6\u5F97\u306B\u5931\u6557\u3057\u307E\u3057\u305F (HTTP " + resp.status + ")");
    const bytes = new Uint8Array(await resp.arrayBuffer());
    if (bytes.length > MAX_BYTES) throw Error("\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u304C\u5BB9\u91CF\u4E0A\u9650\u3092\u8D85\u3048\u307E\u3057\u305F");
    return bytes;
  }
  async function uploadFile(bytes, name, type = "application/octet-stream") {
    if (bytes.length > MAX_BYTES) throw Error("\u30A2\u30C3\u30D7\u30ED\u30FC\u30C9\u5BB9\u91CF\u4E0A\u9650\u3092\u8D85\u3048\u307E\u3057\u305F");
    const form = new FormData();
    form.append("__REQUEST_TOKEN__", K.getRequestToken());
    form.append("file", new Blob([bytes], { type }), name);
    const resp = await fetch("/k/v1/file.json", { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: form });
    if (!resp.ok) throw Error("\u30D5\u30A1\u30A4\u30EB\u306E\u30A2\u30C3\u30D7\u30ED\u30FC\u30C9\u306B\u5931\u6557\u3057\u307E\u3057\u305F (HTTP " + resp.status + "): " + (await resp.text()).slice(0, 300));
    const result = await resp.json();
    if (!result.fileKey) throw Error("\u30D5\u30A1\u30A4\u30EB\u30AD\u30FC\u304C\u8FD4\u3055\u308C\u307E\u305B\u3093\u3067\u3057\u305F");
    return result.fileKey;
  }
  async function backup(app, name) {
    ensureExternalId(app);
    const [fields, layout, records] = await Promise.all([getFields(app), getLayout(app), listRecords(app)]);
    const { zip, hash, manifest } = await makeArchive({ appId: app, fields, layout, records, download: downloadFile });
    const key = await uploadFile(zip, "resoarc-backup-" + app + "-" + (/* @__PURE__ */ new Date()).toISOString().replace(/[:.]/g, "-") + ".zip", "application/zip");
    const record = {
      BackupName: { value: name || "App " + app + " " + manifest.createdAt },
      SourceAppId: { value: String(app) },
      ArchiveHash: { value: hash },
      BackupVersion: { value: String(manifest.version) },
      RecordCount: { value: String(manifest.recordCount) },
      Archive: { value: [{ fileKey: key }] }
    };
    const result = await api("/k/v1/record.json", "POST", { app: managementApp(), record });
    return { id: result.id, manifest, hash, bytes: zip.length };
  }
  async function loadBackup(id) {
    const { record } = await api("/k/v1/record.json", "GET", { app: managementApp(), id });
    const file = record?.Archive?.value?.[0];
    const hash = record?.ArchiveHash?.value;
    if (!file || !hash) throw Error("Archive\u6DFB\u4ED8\u3068ArchiveHash\u3092\u6301\u3064\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u30EC\u30B3\u30FC\u30C9\u3092\u6307\u5B9A\u3057\u3066\u304F\u3060\u3055\u3044");
    if (Number(file.size) > MAX_BYTES) throw Error("ZIP\u306E\u5BB9\u91CF\u4E0A\u9650\u3092\u8D85\u3048\u3066\u3044\u307E\u3059");
    const zip = await downloadFile(file.fileKey);
    const result = await inspectArchive(zip, { expectedHash: hash });
    if (String(result.manifest.sourceAppId) !== String(record?.SourceAppId?.value)) throw Error("\u7BA1\u7406\u30EC\u30B3\u30FC\u30C9\u306E\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u5143ID\u3068ZIP\u304C\u4E00\u81F4\u3057\u307E\u305B\u3093");
    return result;
  }
  function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== void 0) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }
  function addButton(where, text, onClick) {
    const b = el("button", text);
    b.type = "button";
    b.style.cssText = "margin:4px 8px 4px 0;padding:9px 13px;border:1px solid #345f75;border-radius:5px;background:#ecf5f7;color:#173c52;cursor:pointer;font-weight:600";
    b.onclick = onClick;
    where.appendChild(b);
    return b;
  }
  function initialize() {
    const header = K.app.getHeaderMenuSpaceElement();
    if (!header || header.querySelector("[data-resoarc-backup]")) return;
    const root = el("section");
    root.dataset.resoarcBackup = "true";
    root.style.cssText = "padding:9px;margin:8px 0;border:1px solid #b8d0d4;border-radius:8px;background:#f9fcfd;color:#18353b;max-width:980px";
    root.appendChild(el("strong", "ResoArc Backup & Migration | 0.3 alpha"));
    const actions = el("div");
    root.appendChild(actions);
    const msg = el("div", "\u5C02\u7528\u306E\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u7BA1\u7406\u30A2\u30D7\u30EA\u3067\u3059\u3002\u66F8\u304D\u8FBC\u307F\u306F\u624B\u52D5\u64CD\u4F5C\u6642\u3060\u3051\u5B9F\u884C\u3057\u307E\u3059\u3002");
    msg.style.cssText = "white-space:pre-wrap;font-size:13px;margin-top:7px;line-height:1.6";
    root.appendChild(msg);
    const progress = el("div");
    progress.style.cssText = "font-size:13px;color:#394";
    root.appendChild(progress);
    let current = null, draft = null;
    const draftButton = addButton(actions, "\u65B0\u898F\u30A2\u30D7\u30EA\u306E\u4E0B\u66F8\u304D\u3092\u4F5C\u6210 (\u30C7\u30FC\u30BF\u306F\u66F8\u304B\u306A\u3044)", async () => {
      if (!draft) return;
      const plan = draft;
      const typed = window.prompt("\u65B0\u898F\u30A2\u30D7\u30EA\u300C" + plan.name + "\u300D\u3092\u4F5C\u6210\u3057\u3001" + plan.fieldCount + " \u30D5\u30A3\u30FC\u30EB\u30C9\u3092\u8A2D\u5B9A\u3057\u307E\u3059\u3002\n\u65E2\u5B58\u306E\u30A2\u30D7\u30EA\u306B\u306F\u5909\u66F4\u3092\u52A0\u3048\u307E\u305B\u3093\u3002\n\u4F5C\u6210\u3059\u308B\u306B\u306F\u6B21\u3092\u6B63\u78BA\u306B\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044: CREATE " + plan.name, "");
      if (typed !== "CREATE " + plan.name) return;
      if (!window.confirm("\u6700\u7D42\u78BA\u8A8D: \u65B0\u3057\u3044\u30A2\u30D7\u30EA\u306E\u52D5\u4F5C\u30C6\u30B9\u30C8\u74B0\u5883\u306B\u30D5\u30A3\u30FC\u30EB\u30C9\u3092\u8FFD\u52A0\u3057\u307E\u3059\u3002\u30EC\u30B3\u30FC\u30C9\u306E\u5FA9\u5143\u30FB\u30A2\u30D7\u30EA\u8A2D\u5B9A\u306E\u672C\u756A\u53CD\u6620\u306F\u884C\u3044\u307E\u305B\u3093\u3002")) return;
      for (const b of actions.querySelectorAll("button")) b.disabled = true;
      try {
        const done = await createDraftApp(plan, api, (text) => {
          progress.textContent = text;
        });
        msg.textContent = "\u65B0\u898F\u30A2\u30D7\u30EA #" + done.appId + " \u306E\u4E0B\u66F8\u304D\u3092\u4F5C\u6210\u3057\u307E\u3057\u305F\u3002\n\u30A2\u30D7\u30EA\u306E\u7BA1\u7406\u8005\u8A2D\u5B9A\u753B\u9762\u3067\u5185\u5BB9\u3092\u78BA\u8A8D\u3057\u3001\u624B\u52D5\u3067\u300C\u30A2\u30D7\u30EA\u3092\u66F4\u65B0\u300D\u3057\u3066\u304F\u3060\u3055\u3044\u3002\n\u66F4\u65B0\u5F8C\u3001\u5FA9\u5143\u30D7\u30EC\u30D3\u30E5\u30FC\u304B\u3089\u540C\u3058\u30A2\u30D7\u30EAID\u3092\u6307\u5B9A\u3057\u3066\u304F\u3060\u3055\u3044\u3002\n\u30EC\u30B3\u30FC\u30C9\u306F\u307E\u30600\u4EF6\u3001\u65E2\u5B58\u30A2\u30D7\u30EA\u306F\u5909\u66F4\u3057\u3066\u3044\u307E\u305B\u3093\u3002";
        draft = null;
        draftButton.hidden = true;
      } catch (e) {
        msg.textContent = "\u65B0\u898F\u30A2\u30D7\u30EA\u306E\u4F5C\u6210\u51E6\u7406\u304C\u4E2D\u65AD\u3057\u307E\u3057\u305F\u3002\u4F5C\u6210\u3055\u308C\u305F\u30A2\u30D7\u30EA\u304C\u6B8B\u3063\u3066\u3044\u308B\u53EF\u80FD\u6027\u304C\u3042\u308A\u307E\u3059\u3002\n" + e.message;
        console.error(e);
      } finally {
        for (const b of actions.querySelectorAll("button")) b.disabled = false;
      }
    });
    draftButton.hidden = true;
    const restoreButton = addButton(actions, "\u5FA9\u5143\u3092\u5B9F\u884C (\u8FFD\u8A18\u306E\u307F)", async () => {
      if (!current) return;
      const { archive, plan, backupRecordId } = current;
      const confirmText = "RESTORE " + plan.targetAppId + " " + plan.recordCount;
      const typed = window.prompt("\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u30EC\u30B3\u30FC\u30C9 #" + backupRecordId + " \u304B\u3089\u30A2\u30D7\u30EA " + plan.targetAppId + " \u306B " + plan.recordCount + " \u4EF6\u3092\u8FFD\u52A0\u3057\u307E\u3059\u3002\n\u65E2\u5B58\u30C7\u30FC\u30BF\u3092\u524A\u9664\u30FB\u4E0A\u66F8\u304D\u3057\u307E\u305B\u3093\u3002\u5FA9\u5143\u6E08\u307F\u306E\u884C\u306F\u4E00\u610F\u30AD\u30FC\u3067\u8B58\u5225\u3057\u3001\u518D\u958B\u6642\u306B\u30B9\u30AD\u30C3\u30D7\u3057\u307E\u3059\u3002\u8FFD\u52A0\u306E\u53D6\u308A\u6D88\u3057\u306F\u81EA\u52D5\u3067\u306F\u3067\u304D\u307E\u305B\u3093\u3002\n\u5B9F\u884C\u3059\u308B\u306B\u306F\u6B63\u78BA\u306B\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044:\n" + confirmText, "");
      if (typed !== confirmText) return;
      if (!window.confirm("\u6700\u7D42\u78BA\u8A8D: \u30EC\u30B3\u30FC\u30C9\u3092 " + plan.recordCount + " \u4EF6\u8FFD\u52A0\u3057\u307E\u3059\u3002\u8907\u6570\u30D0\u30C3\u30C1\u306E\u9014\u4E2D\u3067\u505C\u6B62\u3057\u305F\u5834\u5408\u3001\u9014\u4E2D\u307E\u3067\u8FFD\u52A0\u6E08\u307F\u306E\u53EF\u80FD\u6027\u304C\u3042\u308A\u307E\u3059\u3002\u5B9F\u884C\u3057\u307E\u3059\u304B\uFF1F")) return;
      restoreButton.disabled = true;
      try {
        const refreshed = await getFields(plan.targetAppId);
        const updatedPlan = createMappedRestorePlan(archive, refreshed, plan.targetAppId, managementApp(), plan.mapping);
        if (JSON.stringify(updatedPlan.mapped) !== JSON.stringify(plan.mapped)) throw Error("\u5FA9\u5143\u5148\u306E\u30D5\u30A3\u30FC\u30EB\u30C9\u5B9A\u7FA9\u304C\u30D7\u30EC\u30D3\u30E5\u30FC\u304B\u3089\u5909\u5316\u3057\u307E\u3057\u305F\u3002\u30D7\u30EC\u30D3\u30E5\u30FC\u3092\u3084\u308A\u76F4\u3057\u3066\u304F\u3060\u3055\u3044");
        const done = await runResumableRestore({
          archive,
          plan,
          api,
          upload: uploadFile,
          onProgress: ({ total, already, added, remaining }) => {
            progress.textContent = "\u5FA9\u5143\u6E08\u307F " + already + " \u4EF6 / \u65B0\u898F\u8FFD\u52A0 " + added + " \u4EF6 / \u6B8B\u308A " + remaining + " \u4EF6\uFF08\u5168 " + total + " \u4EF6\uFF09";
          }
        });
        msg.textContent = "\u5FA9\u5143\u51E6\u7406\u5B8C\u4E86: " + done.added + " \u4EF6\u8FFD\u52A0\u3001" + done.already + " \u4EF6\u306F\u5FA9\u5143\u6E08\u307F\u306E\u305F\u3081\u30B9\u30AD\u30C3\u30D7\u3057\u307E\u3057\u305F\u3002\u5143ID\u3084\u5909\u66F4\u5C65\u6B74\u306F\u7DAD\u6301\u3055\u308C\u307E\u305B\u3093\u3002";
        current = null;
      } catch (e) {
        msg.textContent = "\u5FA9\u5143\u304C\u4E2D\u65AD\u3055\u308C\u307E\u3057\u305F\u3002\u4E00\u90E8\u304C\u8FFD\u52A0\u6E08\u307F\u306E\u53EF\u80FD\u6027\u304C\u3042\u308A\u307E\u3059\u3002\u518D\u5B9F\u884C\u524D\u306B\u5FA9\u5143\u5148\u3092\u78BA\u8A8D\u3057\u3066\u304F\u3060\u3055\u3044\u3002\n" + e.message;
        console.error(e);
      } finally {
        restoreButton.disabled = false;
      }
    });
    restoreButton.hidden = true;
    async function safeRun(job) {
      for (const b of actions.querySelectorAll("button")) b.disabled = true;
      restoreButton.hidden = true;
      current = null;
      draft = null;
      draftButton.hidden = true;
      progress.textContent = "";
      try {
        await job();
      } catch (e) {
        msg.textContent = "\u30A8\u30E9\u30FC: " + e.message;
        console.error(e);
      } finally {
        for (const b of actions.querySelectorAll("button")) b.disabled = false;
      }
    }
    addButton(actions, "\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u3092\u4F5C\u6210", () => safeRun(async () => {
      const input = window.prompt("\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u5143\u30A2\u30D7\u30EAID\u3092\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044\u3002\u7BA1\u7406\u30A2\u30D7\u30EA\u3068\u540C\u3058ID\u306F\u6307\u5B9A\u3067\u304D\u307E\u305B\u3093\u3002", "");
      if (input === null) return;
      const id = positiveId(input);
      ensureExternalId(id);
      const name = window.prompt("\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u540D (\u7A7A\u6B04\u306A\u3089\u81EA\u52D5\u751F\u6210)", "") || "";
      if (!window.confirm("\u30A2\u30D7\u30EA " + id + " \u306E\u30EC\u30B3\u30FC\u30C9\u3068\u6DFB\u4ED8\u30D5\u30A1\u30A4\u30EB\u3092\u8AAD\u307F\u51FA\u3057\u3001\u3053\u306E\u7BA1\u7406\u30A2\u30D7\u30EA\u306BZIP\u3092\u4FDD\u5B58\u3057\u307E\u3059\u3002\u7D9A\u884C\u3057\u307E\u3059\u304B\uFF1F")) return;
      msg.textContent = "\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u3092\u4F5C\u6210\u3057\u3066\u3044\u307E\u3059\u3002\u30D6\u30E9\u30A6\u30B6\u30FC\u3092\u9589\u3058\u306A\u3044\u3067\u304F\u3060\u3055\u3044\u3002";
      const result = await backup(id, name);
      msg.textContent = "\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u4F5C\u6210\u5B8C\u4E86\u3002\u7BA1\u7406\u30EC\u30B3\u30FC\u30C9 #" + result.id + " / " + result.manifest.recordCount + " \u4EF6 / " + result.bytes + " bytes\nSHA-256: " + result.hash;
    }));
    addButton(actions, "\u5FA9\u5143\u30D7\u30EC\u30D3\u30E5\u30FC", () => safeRun(async () => {
      const input = window.prompt("\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u7BA1\u7406\u30A2\u30D7\u30EA\u306E\u30EC\u30B3\u30FC\u30C9ID\u3092\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044", "");
      if (input === null) return;
      const backupRecordId = positiveId(input);
      const targetInput = window.prompt("\u5FA9\u5143\u5148\u306E\u65E2\u5B58\u30A2\u30D7\u30EAID (\u7BA1\u7406\u30A2\u30D7\u30EA\u4EE5\u5916) \u3092\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044", "");
      if (targetInput === null) return;
      const targetId = positiveId(targetInput);
      ensureExternalId(targetId);
      msg.textContent = "\u30A2\u30FC\u30AB\u30A4\u30D6\u3092\u691C\u8A3C\u3057\u3066\u3044\u307E\u3059\u3002";
      const [archive, targetFields] = await Promise.all([loadBackup(backupRecordId), getFields(targetId)]);
      const mapInput = window.prompt('\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9\u5BFE\u5FDC\u8868\u3092JSON\u3067\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044\u3002\n\u540C\u3058\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9\u540C\u58EB\u306A\u3089\u7A7A\u6B04\u3067OK\u3002\n\u4F8B: {"Title":"Name","Rows":"Lines","Rows.Memo":"Lines.Note"}', "");
      if (mapInput === null) return;
      let fieldMap;
      try {
        fieldMap = mapInput.trim() ? JSON.parse(mapInput) : {};
      } catch (e) {
        throw Error("\u5BFE\u5FDC\u8868\u306EJSON\u304C\u4E0D\u6B63\u3067\u3059: " + e.message);
      }
      const plan = createMappedRestorePlan(archive, targetFields, targetId, managementApp(), fieldMap);
      const skipped = plan.skipped.length ? "\n\u79FB\u884C\u5BFE\u8C61\u5916:\n" + plan.skipped.join("\n") : "";
      const resume = await previewRestoreProgress({ archive, plan, api });
      msg.textContent = "\u6574\u5408\u6027\u691C\u8A3C: OK\n\u5143\u30A2\u30D7\u30EA: " + plan.sourceAppId + " / \u5FA9\u5143\u5148: " + targetId + "\n\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u65E5\u6642: " + plan.archiveCreatedAt + "\n\u5168\u5BFE\u8C61: " + plan.recordCount + " \u4EF6 / \u5FA9\u5143\u6E08\u307F: " + resume.already + " \u4EF6 / \u65B0\u898F\u8FFD\u52A0\u4E88\u5B9A: " + resume.remaining + " \u4EF6 / \u30DE\u30C3\u30D7\u3055\u308C\u305F\u9805\u76EE: " + Object.keys(plan.mapped).length + " \u4EF6" + skipped + "\n\u203B\u5FA9\u5143\u5148\u306B\u91CD\u8907\u7981\u6B62\u306E " + MARKER_CODE + " \u304C\u5FC5\u8981\u3067\u3059\u3002\u9014\u4E2D\u3067\u505C\u6B62\u3057\u3066\u3082\u5FA9\u5143\u6E08\u307F\u30EC\u30B3\u30FC\u30C9\u3092\u7167\u5408\u3057\u3066\u518D\u958B\u3067\u304D\u307E\u3059\u3002\u5143ID\u30FB\u30A2\u30AF\u30BB\u30B9\u6A29\u30FB\u76E3\u67FB\u5C65\u6B74\u306F\u5FA9\u5143\u3057\u307E\u305B\u3093\u3002";
      current = { archive, plan, backupRecordId };
      restoreButton.hidden = false;
    }));
    addButton(actions, "\u5916\u90E8ZIP\u304B\u3089\u79FB\u884C\u30D7\u30EC\u30D3\u30E5\u30FC", () => safeRun(async () => {
      const file = await new Promise((resolve) => {
        const input = el("input");
        input.type = "file";
        input.accept = ".zip,application/zip";
        input.onchange = () => resolve(input.files?.[0] || null);
        input.oncancel = () => resolve(null);
        input.click();
      });
      if (!file) return;
      if (file.size > MAX_BYTES) throw Error("ZIP\u306E\u5BB9\u91CF\u4E0A\u9650\uFF0825MiB\uFF09\u3092\u8D85\u3048\u3066\u3044\u307E\u3059");
      const targetInput = window.prompt("\u79FB\u884C\u5148\u306E\u65E2\u5B58\u30A2\u30D7\u30EAID\u3092\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044", "");
      if (targetInput === null) return;
      const targetId = positiveId(targetInput);
      ensureExternalId(targetId);
      msg.textContent = "\u5916\u90E8ZIP\u3092\u691C\u8A3C\u3057\u3066\u3044\u307E\u3059\u3002";
      const archive = await inspectArchive(new Uint8Array(await file.arrayBuffer()));
      const fields = await getFields(targetId);
      const mapInput = window.prompt('\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9\u5BFE\u5FDC\u8868\u3092JSON\u3067\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044\u3002\n\u540C\u3058\u30D5\u30A3\u30FC\u30EB\u30C9\u30B3\u30FC\u30C9\u540C\u58EB\u306A\u3089\u7A7A\u6B04\u3067OK\u3002\n\u4F8B: {"Title":"Name"}', "");
      if (mapInput === null) return;
      let fieldMap;
      try {
        fieldMap = mapInput.trim() ? JSON.parse(mapInput) : {};
      } catch (e) {
        throw Error("\u5BFE\u5FDC\u8868\u306EJSON\u304C\u4E0D\u6B63\u3067\u3059: " + e.message);
      }
      const plan = createMappedRestorePlan(archive, fields, targetId, managementApp(), fieldMap);
      const skipped = plan.skipped.length ? "\n\u79FB\u884C\u5BFE\u8C61\u5916:\n" + plan.skipped.join("\n") : "";
      const resume = await previewRestoreProgress({ archive, plan, api });
      msg.textContent = "\u5916\u90E8ZIP\u306E\u5185\u90E8\u6574\u5408\u6027: OK (\u9001\u4FE1\u5143\u306E\u771F\u6B63\u6027\u306F\u5225\u9014\u78BA\u8A8D\u3057\u3066\u304F\u3060\u3055\u3044)\n\u5143\u30A2\u30D7\u30EA: " + plan.sourceAppId + " / \u79FB\u884C\u5148: " + targetId + "\n\u5168\u5BFE\u8C61: " + plan.recordCount + " \u4EF6 / \u5FA9\u5143\u6E08\u307F: " + resume.already + " \u4EF6 / \u65B0\u898F\u8FFD\u52A0\u4E88\u5B9A: " + resume.remaining + " \u4EF6 / \u30DE\u30C3\u30D7\u9805\u76EE: " + Object.keys(plan.mapped).length + " \u4EF6" + skipped + "\n\u203B\u5FA9\u5143\u5148\u306B\u91CD\u8907\u7981\u6B62\u306E " + MARKER_CODE + " \u304C\u5FC5\u8981\u3067\u3059\u3002\u5143\u306E\u30EC\u30B3\u30FC\u30C9ID\u30FB\u64CD\u4F5C\u5C65\u6B74\u30FB\u30A2\u30AF\u30BB\u30B9\u6A29\u306F\u79FB\u884C\u3067\u304D\u307E\u305B\u3093\u3002";
      current = { archive, plan, backupRecordId: "\u5916\u90E8ZIP" };
      restoreButton.hidden = false;
    }));
    async function showNewAppPreview(archive) {
      const proposed = "ResoArc Copy " + archive.manifest.sourceAppId;
      const name = window.prompt("\u65B0\u3057\u3044\u30A2\u30D7\u30EA\u540D\u3092\u5165\u529B\u3057\u3066\u304F\u3060\u3055\u3044\u3002\u65E2\u5B58\u30A2\u30D7\u30EA\u306F\u5909\u66F4\u3057\u307E\u305B\u3093\u3002", proposed);
      if (name === null) return;
      const plan = planNewApp(archive, name);
      const detail = plan.skipped.length ? "\n\u975E\u5BFE\u5FDC\u30D5\u30A3\u30FC\u30EB\u30C9:\n" + plan.skipped.join("\n") : "";
      msg.textContent = "\u3010\u65B0\u898F\u30A2\u30D7\u30EA\u69CB\u9020\u306E\u30D7\u30EC\u30D3\u30E5\u30FC\u3011\n\u5143\u30A2\u30D7\u30EA: " + plan.sourceAppId + "\n\u4F5C\u6210\u4E88\u5B9A: " + plan.name + "\n\u5BFE\u5FDC\u30D5\u30A3\u30FC\u30EB\u30C9: " + plan.fieldCount + "\n\u30EC\u30B3\u30FC\u30C9\u79FB\u884C\u4E88\u5B9A: \u3053\u306E\u64CD\u4F5C\u3067\u306F 0 \u4EF6\uFF08\u5FA9\u5143\u306F\u5225\u64CD\u4F5C\u3067\u3059\uFF09" + detail + "\n\n\u5236\u7D04:\n" + plan.warnings.join("\n");
      draft = plan;
      draftButton.hidden = false;
    }
    addButton(actions, "\u7BA1\u7406\u30EC\u30B3\u30FC\u30C9\u304B\u3089\u65B0\u898F\u30A2\u30D7\u30EA\u69CB\u9020\u30D7\u30EC\u30D3\u30E5\u30FC", () => safeRun(async () => {
      const input = window.prompt("\u30D0\u30C3\u30AF\u30A2\u30C3\u30D7\u7BA1\u7406\u30A2\u30D7\u30EA\u306E\u30EC\u30B3\u30FC\u30C9ID\u3092\u6307\u5B9A\u3057\u3066\u304F\u3060\u3055\u3044", "");
      if (input === null) return;
      msg.textContent = "\u4FDD\u5B58\u6E08\u307FZIP\u306E\u6574\u5408\u6027\u3092\u691C\u8A3C\u3057\u3066\u3044\u307E\u3059\u3002";
      await showNewAppPreview(await loadBackup(positiveId(input)));
    }));
    addButton(actions, "\u5916\u90E8ZIP\u304B\u3089\u65B0\u898F\u30A2\u30D7\u30EA\u69CB\u9020\u30D7\u30EC\u30D3\u30E5\u30FC", () => safeRun(async () => {
      const file = await new Promise((resolve) => {
        const input = el("input");
        input.type = "file";
        input.accept = ".zip,application/zip";
        input.onchange = () => resolve(input.files?.[0] || null);
        input.oncancel = () => resolve(null);
        input.click();
      });
      if (!file) return;
      if (file.size > MAX_BYTES) throw Error("ZIP\u306E\u5BB9\u91CF\u4E0A\u9650\u3092\u8D85\u3048\u3066\u3044\u307E\u3059");
      msg.textContent = "\u5916\u90E8ZIP\u306E\u6574\u5408\u6027\u3092\u691C\u8A3C\u3057\u3066\u3044\u307E\u3059\u3002";
      await showNewAppPreview(await inspectArchive(new Uint8Array(await file.arrayBuffer())));
    }));
    header.appendChild(root);
  }
  if (K?.events) K.events.on("app.record.index.show", (event) => {
    try {
      initialize();
    } catch (e) {
      console.error("ResoArc Backup init failed", e);
    }
    return event;
  });
})();