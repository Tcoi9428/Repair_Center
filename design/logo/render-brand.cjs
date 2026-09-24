const fs = require('node:fs');
const path = require('node:path');
const sharp = require(process.env.BRAND_SHARP_MODULE || 'sharp');

async function main() {
  const root = path.resolve(__dirname, '../../static/branding');
  await sharp(path.join(root, 'brand-preview.svg')).png().toFile(path.join(root, 'brand-preview.png'));
  const sizes = [16, 24, 32, 48, 180, 192, 512];
  const icons = new Map();
  for (const size of sizes) {
    const output = await sharp(path.join(root, 'favicon.svg')).resize(size, size).png().toBuffer();
    const name = size === 180 ? 'apple-touch-icon.png' : `icon-${size}.png`;
    fs.writeFileSync(path.join(root, name), output);
    icons.set(size, output);
  }
  // ICO directory containing standard PNG image entries at native icon sizes.
  const icoSizes = [16, 32, 48];
  const header = Buffer.alloc(6 + 16 * icoSizes.length);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(icoSizes.length, 4);
  let offset = header.length;
  icoSizes.forEach((size, index) => {
    const entry = 6 + index * 16;
    header[entry] = size;
    header[entry + 1] = size;
    header.writeUInt16LE(1, entry + 4);
    header.writeUInt16LE(32, entry + 6);
    header.writeUInt32LE(icons.get(size).length, entry + 8);
    header.writeUInt32LE(offset, entry + 12);
    offset += icons.get(size).length;
  });
  fs.writeFileSync(path.join(root, 'favicon.ico'), Buffer.concat([header, ...icoSizes.map(size => icons.get(size))]));
  console.log('Rendered brand preview, PNG icons, favicon.ico');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
