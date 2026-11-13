// Minimal zero-dependency ZIP reader, updater and CRC-32 verifier for PPTX packages.
import zlib from 'node:zlib';

const CRC_TABLE = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  let c = i;
  for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
  CRC_TABLE[i] = c >>> 0;
}

const nativeCrc32 = typeof zlib.crc32 === 'function' ? zlib.crc32 : null;

export function crc32(buffer) {
  if (nativeCrc32) return nativeCrc32(buffer) >>> 0;
  let crc = 0xffffffff;
  for (let i = 0; i < buffer.length; i++) {
    crc = CRC_TABLE[(crc ^ buffer[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function findEocd(buffer) {
  const minOffset = Math.max(0, buffer.length - 65557);
  for (let offset = buffer.length - 22; offset >= minOffset; offset--) {
    if (buffer.readUInt32LE(offset) === 0x06054b50) {
      const commentLength = buffer.readUInt16LE(offset + 20);
      if (offset + 22 + commentLength === buffer.length) return offset;
    }
  }
  throw new Error('output is not a valid PPTX ZIP: missing end of central directory');
}

export function readZip(buffer) {
  if (!Buffer.isBuffer(buffer)) buffer = Buffer.from(buffer);
  const eocd = findEocd(buffer);
  const totalEntries = buffer.readUInt16LE(eocd + 10);
  const cdSize = buffer.readUInt32LE(eocd + 12);
  const cdOffset = buffer.readUInt32LE(eocd + 16);
  const commentLen = buffer.readUInt16LE(eocd + 20);
  const comment = buffer.subarray(eocd + 22, eocd + 22 + commentLen);
  if (cdOffset + cdSize > eocd) throw new Error('invalid ZIP central directory bounds');

  const entries = [];
  const byName = new Map();
  let cursor = cdOffset;
  for (let i = 0; i < totalEntries; i++) {
    if (cursor + 46 > eocd || buffer.readUInt32LE(cursor) !== 0x02014b50) {
      throw new Error('corrupt ZIP central directory entry');
    }
    const flags = buffer.readUInt16LE(cursor + 8);
    const method = buffer.readUInt16LE(cursor + 10);
    const dosTime = buffer.readUInt16LE(cursor + 12);
    const dosDate = buffer.readUInt16LE(cursor + 14);
    const crc = buffer.readUInt32LE(cursor + 16);
    const compressedSize = buffer.readUInt32LE(cursor + 20);
    const uncompressedSize = buffer.readUInt32LE(cursor + 24);
    const nameLen = buffer.readUInt16LE(cursor + 28);
    const extraLen = buffer.readUInt16LE(cursor + 30);
    const entryCommentLen = buffer.readUInt16LE(cursor + 32);
    const externalAttr = buffer.readUInt32LE(cursor + 38);
    const localOffset = buffer.readUInt32LE(cursor + 42);
    const name = buffer.toString(flags & 0x0800 ? 'utf8' : 'latin1', cursor + 46, cursor + 46 + nameLen);
    cursor += 46 + nameLen + extraLen + entryCommentLen;

    if (localOffset + 30 > cdOffset || buffer.readUInt32LE(localOffset) !== 0x04034b50) {
      throw new Error(`corrupt ZIP local header for ${name}`);
    }
    const localNameLen = buffer.readUInt16LE(localOffset + 26);
    const localExtraLen = buffer.readUInt16LE(localOffset + 28);
    const dataStart = localOffset + 30 + localNameLen + localExtraLen;
    const dataEnd = dataStart + compressedSize;
    if (dataEnd > cdOffset) throw new Error(`corrupt ZIP entry bounds for ${name}`);

    const entry = {
      name,
      flags,
      method,
      dosTime,
      dosDate,
      crc,
      compressedSize,
      uncompressedSize,
      externalAttr,
      compressed: buffer.subarray(dataStart, dataEnd),
    };
    if (!name.endsWith('/')) {
      if (byName.has(name)) throw new Error(`PPTX contains duplicate package parts: ${name}`);
      byName.set(name, entry);
    }
    entries.push(entry);
  }

  function extract(entry) {
    if (entry.method === 0) return Buffer.from(entry.compressed);
    if (entry.method === 8) return zlib.inflateRawSync(entry.compressed);
    throw new Error(`unsupported ZIP compression method ${entry.method} for ${entry.name}`);
  }

  return {
    entries,
    byName,
    comment,
    has(name) {
      return byName.has(name);
    },
    names() {
      return [...byName.keys()];
    },
    read(name) {
      const entry = byName.get(name);
      if (!entry) throw new Error(`missing ZIP entry: ${name}`);
      return extract(entry);
    },
    verifyAll() {
      for (const entry of entries) {
        if (entry.name.endsWith('/')) continue;
        const data = extract(entry);
        if (data.length !== entry.uncompressedSize || crc32(data) !== entry.crc) {
          throw new Error(`PPTX CRC check failed at: ${entry.name}`);
        }
      }
    },
  };
}

export function writeZip(items, comment = Buffer.alloc(0)) {
  if (items.length > 0xffff) throw new Error('ZIP entry count exceeds 65535 limit');
  const localParts = [];
  const centralParts = [];
  let offset = 0;

  for (const item of items) {
    const nameBuf = Buffer.from(item.name, 'utf8');
    const isAscii = /^[\x00-\x7f]*$/.test(item.name);
    const flags = isAscii ? 0 : 0x0800;
    let method = item.method ?? 8;
    let compressed;
    let uncompressedSize;
    let crc;

    if (item.compressed !== undefined && item.crc !== undefined && item.uncompressedSize !== undefined) {
      compressed = item.compressed;
      uncompressedSize = item.uncompressedSize;
      crc = item.crc;
    } else {
      const raw = Buffer.isBuffer(item.data) ? item.data : Buffer.from(item.data ?? '');
      uncompressedSize = raw.length;
      crc = crc32(raw);
      if (method === 0) {
        compressed = raw;
      } else {
        method = 8;
        compressed = zlib.deflateRawSync(raw);
      }
    }

    if (offset > 0xffffffff) throw new Error('ZIP archive exceeds 4 GiB limit');

    const dosTime = item.dosTime ?? 0;
    const dosDate = item.dosDate ?? 0x0021;
    const externalAttr = item.externalAttr ?? 0;

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(flags, 6);
    local.writeUInt16LE(method, 8);
    local.writeUInt16LE(dosTime, 10);
    local.writeUInt16LE(dosDate, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(compressed.length, 18);
    local.writeUInt32LE(uncompressedSize, 22);
    local.writeUInt16LE(nameBuf.length, 26);
    local.writeUInt16LE(0, 28);
    localParts.push(local, nameBuf, compressed);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(flags, 8);
    central.writeUInt16LE(method, 10);
    central.writeUInt16LE(dosTime, 12);
    central.writeUInt16LE(dosDate, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(compressed.length, 20);
    central.writeUInt32LE(uncompressedSize, 24);
    central.writeUInt16LE(nameBuf.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(externalAttr, 38);
    central.writeUInt32LE(offset, 42);
    centralParts.push(central, nameBuf);

    offset += 30 + nameBuf.length + compressed.length;
  }

  const cdBuf = Buffer.concat(centralParts);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(0, 4);
  eocd.writeUInt16LE(0, 6);
  eocd.writeUInt16LE(items.length, 8);
  eocd.writeUInt16LE(items.length, 10);
  eocd.writeUInt32LE(cdBuf.length, 12);
  eocd.writeUInt32LE(offset, 16);
  eocd.writeUInt16LE(comment.length, 20);

  return Buffer.concat([...localParts, cdBuf, eocd, comment]);
}

export function updateArchive(archive, updates) {
  const map = updates instanceof Map ? updates : new Map(Object.entries(updates ?? {}));
  const items = [];
  const seen = new Set();
  for (const entry of archive.entries) {
    if (map.has(entry.name)) {
      items.push({
        name: entry.name,
        data: map.get(entry.name),
        method: entry.method,
        dosTime: entry.dosTime,
        dosDate: entry.dosDate,
        externalAttr: entry.externalAttr,
      });
      seen.add(entry.name);
    } else {
      items.push(entry);
    }
  }
  for (const [name, data] of map.entries()) {
    if (!seen.has(name)) items.push({ name, data, method: 8 });
  }
  return writeZip(items, archive.comment);
}

export function updateZip(buffer, updates) {
  if (!updates || (updates instanceof Map ? updates.size === 0 : Object.keys(updates).length === 0)) {
    return Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  }
  return updateArchive(readZip(buffer), updates);
}
