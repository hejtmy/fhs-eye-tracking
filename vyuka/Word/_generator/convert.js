// Markdown (Obsidian) → Word, styled per the FHS Psychology Design System.
// usage: node convert.js <vyuka dir> <out dir>
const fs = require('fs');
const path = require('path');
const { marked } = require('marked');
const D = require('docx');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle,
  ShadingType, AlignmentType, ImageRun, Header, Footer, PageNumber, TabStopType, PositionalTab,
  PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader, LevelFormat, CheckBox,
  HeightRule, VerticalAlign, TableLayoutType,
} = D;

const [, , SRC, OUT] = process.argv;
const HERE = __dirname;
const FONTDIR = path.join(process.env.HOME, 'Library/Fonts');

// ---- tokens (tokens.json) ----
const C = {
  black: '0A0A0A', paper: 'FFFFFF', ink70: '353535', ink50: '6A6A6A', ink30: 'A4A4A4',
  ink15: 'D4D4D4', ink05: 'EDEDED', yellow: 'FFD400', magenta: 'FF5CBB',
};
const F = { display: 'Archivo Black', head: 'Archivo', body: 'Instrument Sans', mono: 'JetBrains Mono' };
const pt = (n) => Math.round(n * 2); // half-points
const PAGE_W = 11906, MARGIN = 1077; // A4, 1.9 cm
const TEXT_W = PAGE_W - 2 * MARGIN;
const RULE = 12; // 1.5 pt ≈ the 2px rule
const HAIR = 4;

const font = (f) => fs.readFileSync(path.join(FONTDIR, f));
const FONTS = [
  { name: F.display, data: font('ArchivoBlack-Regular.ttf') },
  { name: F.head, data: font('Archivo-Regular.ttf'), bold: font('Archivo-Bold.ttf') },
  { name: F.body, data: font('InstrumentSans-Regular.ttf'), bold: font('InstrumentSans-Bold.ttf') },
  { name: F.mono, data: font('JetBrainsMono-Regular.ttf'), bold: font('JetBrainsMono-Bold.ttf') },
];
const LOGO = fs.readFileSync(path.join(HERE, 'logo-h.png'));

// ---- per-document context ----
let CTX; // { accent, kind, badge, worksheet }

// ---------- inline rendering ----------
const DOTS = /(\.{4,}|…{2,})/;
function textRuns(text, st) {
  // split long dot fills so they print lighter than the prompt text
  const out = [];
  for (const part of text.split(/(\.{4,})/)) {
    if (!part) continue;
    if (/^\.{4,}$/.test(part)) out.push(new TextRun({ text: part, font: F.body, color: C.ink30, size: st.size }));
    else out.push(run(part, st));
  }
  return out;
}
function run(text, st) {
  return new TextRun({
    text, bold: st.bold, italics: st.italic, strike: st.strike,
    font: st.code ? F.mono : (st.font || F.body),
    size: st.code ? (st.size || pt(11)) - 3 : st.size,
    color: st.color,
    shading: st.code ? { type: ShadingType.CLEAR, fill: C.ink05, color: 'auto' } : undefined,
  });
}
function decode(s) {
  return s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
// returns array of "lines"; each line = array of runs (br splits lines)
function inlineLines(tokens, st = {}) {
  const lines = [[]];
  const push = (r) => lines[lines.length - 1].push(...[].concat(r));
  const walk = (toks, s) => {
    for (const t of toks || []) {
      switch (t.type) {
        case 'text':
        case 'escape':
          if (t.tokens && t.tokens.length) { walk(t.tokens, s); break; }
          decode(t.text).split('\n').forEach((seg, i) => { if (i) lines.push([]); if (seg) push(textRuns(seg, s)); });
          break;
        case 'strong': walk(t.tokens, { ...s, bold: true }); break;
        case 'em': walk(t.tokens, { ...s, italic: true }); break;
        case 'del': walk(t.tokens, { ...s, strike: true }); break;
        case 'codespan': push(run(decode(t.text), { ...s, code: true })); break;
        case 'br': lines.push([]); break;
        case 'link': walk(t.tokens, { ...s, color: '3B56AD' }); break;
        case 'html':
          if (/<br\s*\/?>/i.test(t.text)) lines.push([]);
          break;
        default:
          if (t.text) push(textRuns(decode(t.text), s));
      }
    }
  };
  walk(tokens, st);
  return lines;
}
const plain = (tokens) => (tokens || []).map((t) => (t.tokens ? plain(t.tokens) : decode(t.text || t.raw || ''))).join('');

// ---------- block helpers ----------
const body = (children, o = {}) => new Paragraph({
  children, spacing: { before: 0, after: o.after ?? 100, line: 288 }, indent: o.indent, keepNext: o.keepNext,
  alignment: o.align, ...o.extra,
});

const rightStop = (leader) => [{ type: TabStopType.RIGHT, position: TEXT_W, leader: leader || 'none' }];
function answerLine(indentLeft = 0) {
  return new Paragraph({
    spacing: { before: 280, after: 0 }, indent: { left: indentLeft }, tabStops: rightStop('underscore'),
    children: [new TextRun({ text: '\t', color: C.ink50, font: F.body, size: pt(10) })],
  });
}
const isDotLine = (runsLine, raw) => raw.trim() !== '' && /^[\s.…_]+$/.test(raw);

function numberBadge(num, size) {
  return new TextRun({ text: ` ${num} `, font: F.display, size, color: C.black, shading: { type: ShadingType.CLEAR, fill: CTX.accent, color: 'auto' } });
}

function heading(tok) {
  const text = plain(tok.tokens);
  const m = text.match(/^(\d+[a-z]?)\.\s+(.*)$/);
  if (tok.depth <= 2) {
    const size = pt(15);
    const kids = m ? [numberBadge(m[1], size), new TextRun({ text: '  ' + m[2], font: F.display, size, color: C.black })]
      : [new TextRun({ text, font: F.display, size, color: C.black })];
    return [new Paragraph({
      children: kids, keepNext: true, keepLines: true,
      spacing: { before: 360, after: 140 },
      border: { top: { style: BorderStyle.SINGLE, size: RULE, color: C.black, space: 8 } },
    })];
  }
  const size = pt(12);
  const kids = m ? [numberBadge(m[1], size), new TextRun({ text: '  ' + m[2], font: F.head, bold: true, size })]
    : [new TextRun({ text, font: F.head, bold: true, size })];
  return [new Paragraph({ children: kids, keepNext: true, keepLines: true, spacing: { before: 240, after: 100 } })];
}

// a paragraph token → one or more docx paragraphs
function paragraph(tok, o = {}) {
  const toks = tok.tokens || [];
  const raw = tok.text || '';
  const indentLeft = o.indentLeft || 0;
  // "Jméno: ......" → name field
  if (/^Jméno:\s*\.+\s*$/.test(raw.trim())) {
    return [new Paragraph({
      spacing: { before: 160, after: 240 }, tabStops: rightStop('underscore'),
      children: [
        new TextRun({ text: 'JMÉNO  ', font: F.mono, bold: true, size: pt(8.5), characterSpacing: 16, color: C.black }),
        new TextRun({ text: '\t', color: C.black, size: pt(11) }),
      ],
    })];
  }
  const first = toks[0];
  const meaningful = toks.filter((t) => !(t.type === 'text' && !t.text.trim()));
  // whole paragraph = one code span → formula block
  if (meaningful.length === 1 && meaningful[0].type === 'codespan') {
    return [new Paragraph({
      spacing: { before: 60, after: 140 }, indent: { left: indentLeft },
      shading: { type: ShadingType.CLEAR, fill: C.ink05, color: 'auto' },
      border: { left: { style: BorderStyle.SINGLE, size: RULE, color: C.black, space: 6 } },
      children: [new TextRun({ text: decode(meaningful[0].text), font: F.mono, size: pt(10) })],
    })];
  }
  // whole paragraph bold
  if (meaningful.length === 1 && first.type === 'strong') {
    const t = plain(first.tokens);
    if (/[=×÷]/.test(t)) { // formula
      return [new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160 },
        border: ['top', 'bottom', 'left', 'right'].reduce((a, k) => ({ ...a, [k]: { style: BorderStyle.SINGLE, size: RULE, color: C.black, space: 6 } }), {}),
        children: [new TextRun({ text: t, font: F.head, bold: true, size: pt(13) })],
      })];
    }
    const m = t.match(/^(\d+)\.\s+(.*)$/);
    return [new Paragraph({
      keepNext: true, spacing: { before: 200, after: 80 }, indent: { left: indentLeft },
      children: m ? [numberBadge(m[1], pt(11.5)), new TextRun({ text: '  ' + m[2], font: F.head, bold: true, size: pt(11.5) })]
        : [new TextRun({ text: t, font: F.head, bold: true, size: pt(11.5) })],
    })];
  }
  // bold lead-in followed by text
  if (first && first.type === 'strong' && meaningful.length > 1) {
    const lead = plain(first.tokens);
    const m = lead.match(/^(\d+)\.\s+(.*)$/);
    const rest = inlineLines(toks.slice(1));
    if (m) { // numbered step: mini heading + rest
      const lines = rest;
      lines[0] = [numberBadge(m[1], pt(11.5)), new TextRun({ text: '  ' + m[2], font: F.head, bold: true, size: pt(11.5) }), ...lines[0]];
      return linesToParas(lines, { indentLeft, before: 200 });
    }
    // callout card
    const lines = inlineLines(toks);
    const runs = [];
    lines.forEach((l, i) => { if (i) runs.push(new TextRun({ break: 1 })); runs.push(...l); });
    const b = { style: BorderStyle.SINGLE, size: RULE, color: C.black, space: 6 };
    return [new Paragraph({
      children: runs, spacing: { before: 140, after: 220, line: 288 }, indent: { left: indentLeft + 120, right: 120 },
      shading: { type: ShadingType.CLEAR, fill: CTX.accent, color: 'auto' },
      border: { top: b, bottom: b, left: b, right: b },
    })];
  }
  return linesToParas(inlineLines(toks), { indentLeft, rawLines: raw.split('\n') });
}

function linesToParas(lines, o = {}) {
  const out = [];
  let buf = [];
  const flush = () => {
    if (!buf.length) return;
    const runs = [];
    buf.forEach((l, i) => { if (i) runs.push(new TextRun({ break: 1 })); runs.push(...l); });
    out.push(new Paragraph({ children: runs, spacing: { before: out.length ? 0 : (o.before || 0), after: 120, line: 300 }, indent: { left: o.indentLeft || 0 } }));
    buf = [];
  };
  lines.forEach((l, i) => {
    const txt = l.map((r) => r.__text ?? '').join('');
    const raw = o.rawLines && o.rawLines[i] !== undefined ? o.rawLines[i] : null;
    if (raw !== null && isDotLine(l, raw)) { flush(); out.push(answerLine(o.indentLeft || 0)); return; }
    if (l.length) buf.push(l);
  });
  flush();
  return out;
}

// ---------- lists ----------
function list(tok, depth = 0) {
  const out = [];
  const base = depth * 400;
  tok.items.forEach((item, idx) => {
    const blocks = item.tokens || [];
    let firstDone = false;
    for (const b of blocks) {
      if (b.type === 'space' || b.type === 'checkbox') continue;
      if (b.type === 'list') { out.push(...list(b, depth + 1)); continue; }
      if (!firstDone && (b.type === 'text' || b.type === 'paragraph')) {
        firstDone = true;
        const lines = inlineLines(b.tokens || [{ type: 'text', text: b.text }]);
        const runs = [];
        lines.forEach((l, i) => { if (i) runs.push(new TextRun({ break: 1 })); runs.push(...l); });
        if (item.task) {
          out.push(new Paragraph({
            children: [new CheckBox({ checked: !!item.checked, checkedState: { value: '2612', font: 'MS Gothic' }, uncheckedState: { value: '2610', font: 'MS Gothic' } }), new TextRun({ text: '\t' }), ...runs],
            tabStops: [{ type: TabStopType.LEFT, position: base + 400 }],
            indent: { left: base + 400, hanging: 400 }, spacing: { after: 90, line: 288 },
          }));
        } else if (tok.ordered) {
          const n = (tok.start === '' ? 1 : Number(tok.start || 1)) + idx;
          out.push(new Paragraph({
            children: [new TextRun({ text: `${n}.`, font: F.head, bold: true }), new TextRun({ text: '\t' }), ...runs],
            tabStops: [{ type: TabStopType.LEFT, position: base + 400 }],
            indent: { left: base + 400, hanging: 400 }, spacing: { after: 100, line: 288 },
          }));
        } else {
          out.push(new Paragraph({ children: runs, numbering: { reference: 'sq', level: Math.min(depth, 1) }, spacing: { after: 80, line: 288 } }));
        }
        continue;
      }
      out.push(...block(b, { indentLeft: base + 400 }));
    }
  });
  if (out.length) out.push(new Paragraph({ children: [], spacing: { after: 60 } }));
  return out;
}

// ---------- tables ----------
function cellLines(cell) { return inlineLines(cell.tokens); }
function table(tok) {
  const ncol = tok.header.length;
  const small = ncol >= 6;
  const fs_ = small ? pt(9) : pt(10);
  const brCount = (c) => (c.text.match(/<br\s*\/?>/gi) || []).length;
  const isEmpty = (c) => !c.text.replace(/<br\s*\/?>/gi, '').trim();
  // widths
  const w = [];
  for (let j = 0; j < ncol; j++) {
    const head = plain(tok.header[j].tokens);
    const lens = tok.rows.map((r) => (isEmpty(r[j]) ? 0 : plain(r[j].tokens).length));
    const maxBody = Math.max(0, ...lens);
    const allEmpty = tok.rows.every((r) => isEmpty(r[j]));
    let weight = Math.max(Math.min(head.length, 18) * 0.9, Math.min(maxBody, 60));
    if (allEmpty) weight = Math.max(head.length * 0.9, CTX.worksheet ? 14 : 8);
    if (tok.rows.some((r) => brCount(r[j]) > 0)) weight = Math.max(weight, 28);
    w.push(Math.max(weight, 3.5));
  }
  // minimum width per column = its longest unbreakable word (header or body) + cell margins
  const fsPt = small ? 9 : 10;
  const longestWord = (s) => Math.max(0, ...s.split(/[\s/]+/).map((x) => x.length));
  const mins = [];
  for (let j = 0; j < ncol; j++) {
    const hw = Math.min(longestWord(plain(tok.header[j].tokens)), 20) * fsPt * 13.5; // Archivo Bold is wide
    const bw = Math.min(longestWord(tok.rows.map((r) => plain(r[j].tokens)).join(' ')), 22) * fsPt * 11.5;
    mins.push(Math.max(small ? 520 : 640, hw + 240, bw + 240));
  }
  const minSum = mins.reduce((a, b) => a + b, 0);
  let widths;
  if (minSum >= TEXT_W) widths = mins.map((m) => Math.floor((m / minSum) * TEXT_W));
  else {
    // every column gets its minimum, the rest of the line is shared by content weight
    const spare = TEXT_W - minSum;
    const sum = w.reduce((a, b) => a + b, 0);
    widths = mins.map((m, j) => Math.floor(m + (w[j] / sum) * spare));
  }
  widths[widths.length - 1] += TEXT_W - widths.reduce((a, b) => a + b, 0);

  const align = (j) => ({ right: AlignmentType.RIGHT, center: AlignmentType.CENTER }[tok.align[j]] || AlignmentType.LEFT);
  const headerIsBlank = tok.header.every((h) => !h.text.trim());
  const mkCell = (cell, j, isHead) => {
    const lines = cellLines(cell);
    const runs = [];
    lines.forEach((l, i) => {
      if (!l.length) return;
      if (runs.length) runs.push(new TextRun({ break: 1 }));
      if (isHead) runs.push(new TextRun({ text: plain(cell.tokens), font: F.head, bold: true, size: fs_, color: C.paper }));
      else runs.push(...l.map((r) => r));
    });
    const firstColLabel = !isHead && j === 0 && !isEmpty(cell) && tok.header[0] && !plain(tok.header[0].tokens).trim();
    return new TableCell({
      width: { size: widths[j], type: WidthType.DXA },
      shading: isHead ? { type: ShadingType.CLEAR, fill: C.black, color: 'auto' }
        : (firstColLabel ? { type: ShadingType.CLEAR, fill: C.ink05, color: 'auto' } : undefined),
      margins: { top: 50, bottom: 50, left: 90, right: 90 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ alignment: align(j), spacing: { after: 0, line: 264 }, children: isHead ? runs.slice(0, 1) : runs.map((r) => r) })],
    });
  };
  // body runs need table font size: rebuild runs with size
  const sizeRuns = (cell) => { cell.tokens = cell.tokens; return cell; };
  const rows = [];
  if (!headerIsBlank) {
    rows.push(new TableRow({ tableHeader: true, cantSplit: true, children: tok.header.map((h, j) => mkCell(h, j, true)) }));
  }
  const prevSize = CTX.size; CTX.size = fs_;
  tok.rows.forEach((r) => {
    const maxBr = Math.max(0, ...r.map(brCount));
    const hasEmpty = r.some(isEmpty);
    let h;
    if (maxBr) h = 260 * maxBr + 200;
    else if (hasEmpty && CTX.worksheet) h = 420;
    rows.push(new TableRow({
      cantSplit: true,
      height: h ? { value: h, rule: HeightRule.ATLEAST } : undefined,
      children: r.map((c, j) => {
        const lines = inlineLines(c.tokens, { size: fs_ });
        const runs = [];
        lines.forEach((l) => { if (!l.length) return; if (runs.length) runs.push(new TextRun({ break: 1 })); runs.push(...l); });
        const firstColLabel = j === 0 && !isEmpty(c) && headerIsBlank === false && !plain(tok.header[0].tokens).trim();
        return new TableCell({
          width: { size: widths[j], type: WidthType.DXA },
          shading: firstColLabel ? { type: ShadingType.CLEAR, fill: C.ink05, color: 'auto' }
            : (c.text.trim() === '–' && ncol > 3 ? { type: ShadingType.CLEAR, fill: C.ink15, color: 'auto' } : undefined),
          margins: { top: 50, bottom: 50, left: 90, right: 90 },
          verticalAlign: maxBr ? VerticalAlign.TOP : VerticalAlign.CENTER,
          children: [new Paragraph({ alignment: align(j), spacing: { after: 0, line: 264 }, children: runs })],
        });
      }),
    }));
  });
  CTX.size = prevSize;
  const outer = { style: BorderStyle.SINGLE, size: RULE, color: C.black };
  const inner = { style: BorderStyle.SINGLE, size: HAIR, color: C.ink30 };
  return [
    new Table({
      width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
      borders: { top: outer, bottom: outer, left: outer, right: outer, insideHorizontal: inner, insideVertical: inner },
      rows,
    }),
    new Paragraph({ children: [], spacing: { after: 120 } }),
  ];
}

// ---------- dispatcher ----------
function block(tok, o = {}, next) {
  switch (tok.type) {
    case 'heading': return heading(tok);
    case 'paragraph': return paragraph(tok, o);
    case 'text': return paragraph({ ...tok, tokens: tok.tokens || [{ type: 'text', text: tok.text }] }, o);
    case 'list': return list(tok);
    case 'table': return table(tok);
    case 'hr':
      if (next && next.type === 'heading') return [];
      return [new Paragraph({ children: [], spacing: { before: 120, after: 200 }, border: { bottom: { style: BorderStyle.SINGLE, size: RULE, color: C.black, space: 1 } } })];
    case 'code':
      return tok.text.split('\n').map((l) => new Paragraph({ shading: { type: ShadingType.CLEAR, fill: C.ink05, color: 'auto' }, spacing: { after: 0 }, children: [new TextRun({ text: l || ' ', font: F.mono, size: pt(9.5) })] }));
    case 'blockquote': return (tok.tokens || []).flatMap((t) => block(t, { indentLeft: 400 }));
    case 'html':
      if (/<br/i.test(tok.text)) return [new Paragraph({ children: [], spacing: { after: 0, line: 240 * ((tok.text.match(/<br/gi) || []).length) } })];
      return [];
    case 'space': return [];
    default: return tok.text ? [body([run(tok.text, {})])] : [];
  }
}

// patch: TextRun size inheritance inside tables (CTX.size) — wrap run()
const _run = run;
// eslint-disable-next-line no-func-assign
run = function (text, st) { return _run(text, { ...st, size: st.size || CTX.size }); };

// ---------- document ----------
function build(md, meta) {
  CTX = { ...meta, size: undefined };
  md = md.replace(/\[\[([^\]|]+)(\|([^\]]+))?\]\]/g, (_, a, __, b) => `*${b || a}*`);
  const tokens = marked.lexer(md, { gfm: true, breaks: true });
  const h1i = tokens.findIndex((t) => t.type === 'heading' && t.depth === 1);
  const h1 = h1i >= 0 ? plain(tokens[h1i].tokens) : meta.title;
  if (h1i >= 0) tokens.splice(h1i, 1);
  const title = meta.titleFrom ? meta.titleFrom(h1) : h1;

  const children = [
    new Paragraph({
      spacing: { before: 120, after: 80 },
      children: [new TextRun({ text: ` ${meta.eyebrow} `, font: F.head, bold: true, size: pt(9), characterSpacing: 16, color: C.black, shading: { type: ShadingType.CLEAR, fill: meta.accent, color: 'auto' } })],
    }),
    new Paragraph({
      spacing: { before: 0, after: 200, line: 228 }, keepNext: true,
      children: [new TextRun({ text: title, font: F.display, size: pt(26), color: C.black })],
    }),
  ];
  tokens.forEach((t, i) => children.push(...block(t, {}, tokens[i + 1])));

  const header = new Header({
    children: [new Paragraph({
      spacing: { after: 0 }, tabStops: rightStop(),
      border: { bottom: { style: BorderStyle.SINGLE, size: RULE, color: C.black, space: 4 } },
      children: [
        new ImageRun({ type: 'png', data: LOGO, transformation: { width: 71, height: 48 }, altText: { title: 'FHS UK', description: 'Logo FΨS', name: 'logo' } }),
        new TextRun({ text: '\t' }),
        new TextRun({ text: 'EYE-TRACKING V PSYCHOLOGICKÉM VÝZKUMU   ', font: F.mono, size: pt(7.5), color: C.ink70, characterSpacing: 10 }),
        new TextRun({ text: ` ${meta.badge} `, font: F.display, size: pt(10), color: C.black, shading: { type: ShadingType.CLEAR, fill: meta.accent, color: 'auto' } }),
      ],
    })],
  });
  const fr = { font: F.mono, size: pt(7.5), color: C.ink70, characterSpacing: 8 };
  const footer = new Footer({
    children: [new Paragraph({
      border: { top: { style: BorderStyle.SINGLE, size: HAIR, color: C.black, space: 4 } }, tabStops: rightStop(),
      children: [
        new TextRun({ text: 'FHS UK · KATEDRA PSYCHOLOGIE A VĚD O ŽIVOTĚ', ...fr }),
        new TextRun({ text: '\t' }),
        new TextRun({ text: `${meta.short.toUpperCase()} · `, ...fr }),
        new TextRun({ children: [PageNumber.CURRENT], ...fr, bold: true, color: C.black }),
        new TextRun({ text: ' / ', ...fr }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], ...fr }),
      ],
    })],
  });

  return new Document({
    creator: 'Katedra psychologie a věd o životě FHS UK',
    title: `${meta.badge} – ${title}`,
    fonts: FONTS,
    styles: {
      default: { document: { run: { font: F.body, size: pt(10.5), color: C.black }, paragraph: { spacing: { line: 288 } } } },
    },
    numbering: {
      config: [{
        reference: 'sq',
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: '■', alignment: AlignmentType.LEFT, style: { run: { font: 'Arial', size: pt(7) }, paragraph: { indent: { left: 400, hanging: 300 } } } },
          { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 800, hanging: 300 } } } },
        ],
      }],
    },
    sections: [{
      properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 1300, bottom: 1100, left: MARGIN, right: MARGIN, header: 560, footer: 520 } } },
      headers: { default: header }, footers: { default: footer }, children,
    }],
  });
}

// ---------- jobs ----------
const YELLOW = C.yellow, PINK = C.magenta;
const jobs = [];
const plDir = path.join(SRC, 'Pracovní listy');
for (const f of fs.readdirSync(plDir).filter((x) => x.endsWith('.md')).sort()) {
  const m = f.match(/^PL (\d+) – (.+)\.md$/);
  if (m) {
    jobs.push({ src: path.join(plDir, f), out: path.join(OUT, 'Pracovní listy', f.replace(/\.md$/, '.docx')), meta: {
      accent: YELLOW, worksheet: true, eyebrow: `PRACOVNÍ LIST ${m[1]}`, badge: `PL ${m[1]}`, short: `PL ${m[1]}`,
      titleFrom: (h) => h.replace(/^PL \d+ – /, ''),
    } });
  } else if (f.startsWith('Tahák')) {
    jobs.push({ src: path.join(plDir, f), out: path.join(OUT, 'Pracovní listy', f.replace(/\.md$/, '.docx')), meta: {
      accent: YELLOW, worksheet: true, eyebrow: 'TAHÁK · NECHTE SI PO RUCE', badge: 'TAHÁK', short: 'Tahák',
      titleFrom: (h) => h.replace(/^Tahák – /, '').replace(/^./, (c) => c.toUpperCase()),
    } });
  }
}
for (const f of fs.readdirSync(SRC).filter((x) => /^Lektor – .+\.md$/.test(x)).sort()) {
  const short = f.replace(/^Lektor – /, '').replace(/\.md$/, '');
  jobs.push({ src: path.join(SRC, f), out: path.join(OUT, 'Lektor', f.replace(/\.md$/, '.docx')), meta: {
    accent: PINK, worksheet: false, eyebrow: 'PRO LEKTORA', badge: 'LEKTOR', short: `Lektor · ${short}`,
  } });
}

(async () => {
  for (const j of jobs) {
    fs.mkdirSync(path.dirname(j.out), { recursive: true });
    const doc = build(fs.readFileSync(j.src, 'utf8'), j.meta);
    fs.writeFileSync(j.out, await Packer.toBuffer(doc));
    console.log('wrote', path.relative(OUT, j.out));
  }
})();
