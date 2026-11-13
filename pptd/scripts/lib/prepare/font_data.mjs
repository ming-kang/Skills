// TrueType/TTC metadata and uncompressed EOT wrapping (Node stdlib only).

const MAC_ROMAN_HIGH =
  'ÄÅÇÉÑÖÜáàâäãåçéèêëíìîïñóòôöõúùûü' +
  '†°¢£§•¶ß®©™´¨≠ÆØ∞±≤≥¥µ∂∑∏π∫ªºΩæø' +
  '¿¡¬√ƒ≈∆«»…\u00a0ÀÃÕŒœ–—“”‘’÷◊ÿŸ⁄€‹›ﬁﬂ' +
  '‡·‚„‰ÂÊÁËÈÍÎÏÌÓÔ\uf8ffÒÚÛÙıˆ˜¯˘˙˚¸˝˛ˇ';

function decodeMacRoman(bytes) {
  let out = '';
  for (let i = 0; i < bytes.length; i++) {
    const b = bytes[i];
    out += b < 0x80 ? String.fromCharCode(b) : MAC_ROMAN_HIGH[b - 0x80];
  }
  return out;
}

function decodeUtf16BE(bytes) {
  let out = '';
  for (let i = 0; i + 1 < bytes.length; i += 2) {
    out += String.fromCharCode((bytes[i] << 8) | bytes[i + 1]);
  }
  return out;
}

function decodeUtf16LE(bytes) {
  return Buffer.from(bytes).toString('utf16le');
}

function encodeUtf16LE(text) {
  return Buffer.from(text, 'utf16le');
}

export function sfntTables(data, offset = 0) {
  const sig = data.subarray(offset, offset + 4);
  const isSfnt = (sig[0] === 0 && sig[1] === 1 && sig[2] === 0 && sig[3] === 0) ||
    sig.toString('ascii') === 'true' || sig.toString('ascii') === 'OTTO';
  if (!isSfnt) throw new Error('only OpenType/TrueType font containers are supported');
  const count = data.readUInt16BE(offset + 4);
  if (!(count > 0 && count <= 256) || offset + 12 + count * 16 > data.length) {
    throw new Error('invalid font table directory');
  }
  const tables = new Map();
  for (let i = 0; i < count; i++) {
    const pos = offset + 12 + i * 16;
    const tag = data.subarray(pos, pos + 4).toString('ascii');
    const checksum = data.readUInt32BE(pos + 4);
    const start = data.readUInt32BE(pos + 8);
    const length = data.readUInt32BE(pos + 12);
    if (start + length > data.length || tables.has(tag)) {
      throw new Error('invalid or duplicated font table');
    }
    tables.set(tag, { checksum, start, length });
  }
  return tables;
}

function readTable(data, tables, tag) {
  const entry = tables.get(tag);
  if (!entry) throw new Error(`font is missing ${tag} metadata`);
  return data.subarray(entry.start, entry.start + entry.length);
}

function readNames(data, tables) {
  const table = readTable(data, tables, 'name');
  const count = table.readUInt16BE(2);
  const strings = table.readUInt16BE(4);
  if (6 + count * 12 > table.length) throw new Error('invalid font name table');
  const selected = new Map();
  const aliases = new Set();
  for (let i = 0; i < count; i++) {
    const pos = 6 + i * 12;
    const platform = table.readUInt16BE(pos);
    const encoding = table.readUInt16BE(pos + 2);
    const language = table.readUInt16BE(pos + 4);
    const key = table.readUInt16BE(pos + 6);
    const length = table.readUInt16BE(pos + 8);
    const offset = table.readUInt16BE(pos + 10);
    if (![1, 2, 4, 5, 16, 17].includes(key)) continue;
    if (strings + offset + length > table.length) throw new Error('invalid font name bounds');
    const raw = table.subarray(strings + offset, strings + offset + length);
    let text;
    let rank;
    if (platform === 3 && (encoding === 0 || encoding === 1 || encoding === 10)) {
      text = decodeUtf16BE(raw);
      rank = language === 0x0409 ? 0 : 3;
    } else if (platform === 0) {
      text = decodeUtf16BE(raw);
      rank = 1;
    } else if (platform === 1 && encoding === 0) {
      text = decodeMacRoman(raw);
      rank = language === 0 ? 2 : 4;
    } else {
      continue;
    }
    text = text.replace(/^[\x00 ]+|[\x00 ]+$/g, '');
    if (key === 1 && text) aliases.add(text);
    const prev = selected.get(key);
    if (!prev || rank < prev.rank) selected.set(key, { rank, text });
  }
  const names = {};
  for (const [key, { text }] of selected.entries()) names[key] = text;
  return { names, aliases };
}

function inferStyle(subfamily, italicFlag = false) {
  const name = subfamily.replace(/\s+/g, '').toLowerCase();
  const bold = name === 'bold' || name === 'bolditalic' || name === 'boldoblique';
  const italic = name === 'italic' || name === 'oblique' || name === 'bolditalic' || name === 'boldoblique' || (!name && italicFlag);
  return bold && italic ? 'boldItalic' : bold ? 'bold' : italic ? 'italic' : 'regular';
}

function inferPitch(panose) {
  if (panose[3] === 9) return 49;
  if (panose[1] >= 2 && panose[1] <= 10) return 18;
  return 34;
}

function inferCharset(codepages) {
  for (const [bit, charset] of [[18, 134], [17, 128], [20, 136], [19, 129], [31, 2]]) {
    if (codepages & (1 << bit)) return charset > 127 ? charset - 256 : charset;
  }
  return 0;
}

export function readFontFaces(buffer) {
  const data = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  if (data.length >= 82 && data.readUInt16LE(34) === 0x504c) {
    const total = data.readUInt32LE(0);
    const size = data.readUInt32LE(4);
    const version = data.readUInt32LE(8);
    const flags = data.readUInt32LE(12);
    if (total !== data.length || !(size > 0 && size < total) || (version !== 0x20001 && version !== 0x20002) || (flags & ~4)) {
      throw new Error('invalid or unsupported EOT font');
    }
    let offset = 82;
    const names = [];
    for (let i = 0; i < 4; i++) {
      const length = data.readUInt16LE(offset);
      offset += 2;
      if (offset + length + 2 > total - size) throw new Error('invalid EOT name bounds');
      names.push(decodeUtf16LE(data.subarray(offset, offset + length)));
      offset += length + 2;
    }
    return [{
      family: names[0],
      aliases: [names[0]],
      slot: inferStyle(names[1], Boolean(data[27])),
      face: 0,
      fsType: data.readUInt16LE(32),
      charset: inferCharset(data.readUInt32LE(52)),
      pitchFamily: inferPitch(data.subarray(16, 26)),
      eot: true,
      variable: false,
      trueType: true,
      cjk: Boolean(data.readUInt32LE(40) & (1 << 27)),
    }];
  }

  let offsets = [0];
  if (data.subarray(0, 4).toString('ascii') === 'ttcf') {
    const count = data.readUInt32BE(8);
    if (!(count > 0 && count <= 256) || 12 + count * 4 > data.length) {
      throw new Error('invalid TrueType collection');
    }
    offsets = Array.from({ length: count }, (_, i) => data.readUInt32BE(12 + i * 4));
  }

  return offsets.map((offset, face) => {
    const tables = sfntTables(data, offset);
    const { names, aliases } = readNames(data, tables);
    const os2 = readTable(data, tables, 'OS/2');
    const head = readTable(data, tables, 'head');
    if (os2.length < 78 || head.length < 54 || !names[1]) {
      throw new Error('incomplete TrueType font metadata');
    }
    return {
      family: names[1],
      aliases: [...aliases].sort(),
      slot: inferStyle(names[2] ?? '', Boolean(os2.readUInt16BE(62) & 1)),
      face,
      fsType: os2.readUInt16BE(8),
      charset: inferCharset(os2.length >= 86 ? os2.readUInt32BE(78) : 0),
      pitchFamily: inferPitch(os2.subarray(32, 42)),
      eot: false,
      variable: tables.has('fvar'),
      trueType: tables.has('glyf'),
      cjk: Boolean(os2.readUInt32BE(46) & (1 << 27)),
    };
  });
}

function tableChecksum(bytes) {
  const pad = (4 - (bytes.length % 4)) % 4;
  const padded = pad ? Buffer.concat([bytes, Buffer.alloc(pad)]) : bytes;
  let sum = 0;
  for (let i = 0; i < padded.length; i += 4) {
    sum = (sum + padded.readUInt32BE(i)) >>> 0;
  }
  return sum;
}

export function extractTtcFace(buffer, face) {
  const data = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  if (data.subarray(0, 4).toString('ascii') !== 'ttcf') {
    if (face !== 0) throw new Error('a TTF has only one face');
    return data;
  }
  const totalFaces = data.readUInt32BE(8);
  if (face < 0 || face >= totalFaces) throw new Error('invalid collection face index');
  const tables = sfntTables(data, data.readUInt32BE(12 + face * 4));
  const tags = [...tables.keys()].filter((tag) => tag !== 'DSIG').sort();
  const count = tags.length;
  const selector = 31 - Math.clz32(count);
  const searchRange = 16 * (1 << selector);
  const header = Buffer.alloc(12 + count * 16);
  header.writeUInt32BE(0x10000, 0);
  header.writeUInt16BE(count, 4);
  header.writeUInt16BE(searchRange, 6);
  header.writeUInt16BE(selector, 8);
  header.writeUInt16BE(count * 16 - searchRange, 10);

  const chunks = [header];
  let cursor = header.length;
  let headOffset = null;
  for (let i = 0; i < count; i++) {
    const tag = tags[i];
    const raw = Buffer.from(readTable(data, tables, tag));
    if (tag === 'head') {
      raw.fill(0, 8, 12);
      headOffset = cursor;
    }
    const dir = 12 + i * 16;
    header.write(tag, dir, 4, 'ascii');
    header.writeUInt32BE(tableChecksum(raw), dir + 4);
    header.writeUInt32BE(cursor, dir + 8);
    header.writeUInt32BE(raw.length, dir + 12);
    chunks.push(raw);
    cursor += raw.length;
    const pad = (4 - (raw.length % 4)) % 4;
    if (pad) {
      chunks.push(Buffer.alloc(pad));
      cursor += pad;
    }
  }
  if (headOffset === null) throw new Error('collection member has no head table');
  const output = Buffer.concat(chunks);
  output.writeUInt32BE((0xb1b0afba - tableChecksum(output)) >>> 0, headOffset + 8);
  return output;
}

export function embeddingAllowed(face) {
  const flags = face.fsType;
  return !(flags & 0x0200) && (!(flags & 0x000e) || Boolean(flags & 0x0008)) && !face.variable && face.trueType;
}

export function ttfToEot(buffer) {
  const data = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  const face = readFontFaces(data)[0];
  if (face.eot) {
    if (!embeddingAllowed(face)) throw new Error('font does not permit editable outline embedding');
    return data;
  }
  if (!embeddingAllowed(face)) throw new Error('font is variable or does not permit editable outline embedding');
  const tables = sfntTables(data);
  if (!tables.has('glyf')) throw new Error('font has no TrueType outlines');
  const os2 = readTable(data, tables, 'OS/2');
  const head = readTable(data, tables, 'head');
  const { names } = readNames(data, tables);

  const header = Buffer.alloc(82);
  header.writeUInt32LE(0, 0);
  header.writeUInt32LE(data.length, 4);
  header.writeUInt32LE(0x20001, 8);
  header.writeUInt32LE(0, 12);
  os2.copy(header, 16, 32, 42);
  header.writeUInt8(1, 26);
  header.writeUInt8(os2.readUInt16BE(62) & 1 ? 1 : 0, 27);
  header.writeUInt16LE(os2.readUInt16BE(4), 28);
  header.writeUInt16LE(face.fsType, 32);
  header.writeUInt16LE(0x504c, 34);
  for (let i = 0; i < 4; i++) header.writeUInt32LE(os2.readUInt32BE(42 + i * 4), 36 + i * 4);
  const hasCodePages = os2.length >= 86 && os2.readUInt16BE(0) >= 1;
  header.writeUInt32LE(hasCodePages ? os2.readUInt32BE(78) : 0, 52);
  header.writeUInt32LE(hasCodePages ? os2.readUInt32BE(82) : 0, 56);
  header.writeUInt32LE(head.readUInt32BE(8), 60);

  const nameChunks = [header];
  for (const key of [1, 2, 5, 4]) {
    const raw = encodeUtf16LE(names[key] ?? names[1]);
    if (raw.length > 65535) throw new Error('font name is too long for EOT');
    const len = Buffer.alloc(2);
    len.writeUInt16LE(raw.length, 0);
    nameChunks.push(len, raw, Buffer.alloc(2));
  }
  nameChunks.push(Buffer.alloc(2));
  const fullHeader = Buffer.concat(nameChunks);
  fullHeader.writeUInt32LE(fullHeader.length + data.length, 0);
  return Buffer.concat([fullHeader, data]);
}
