// website/scripts/generate-assets.mjs
import sharp from 'sharp';
import { readFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

try {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const publicDir = join(__dirname, '../public');
  const svgPath = join(publicDir, 'favicon.svg');
  const svg = readFileSync(svgPath);

  mkdirSync(join(publicDir, 'og'), { recursive: true });

  // Favicon PNGs
  await sharp(svg).resize(16, 16).png().toFile(join(publicDir, 'favicon-16.png'));
  await sharp(svg).resize(32, 32).png().toFile(join(publicDir, 'favicon-32.png'));
  await sharp(svg).resize(180, 180).png().toFile(join(publicDir, 'apple-touch-icon.png'));

  // OG image — 1200×630 dark card with wordmark
  const ogSvg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#818cf8"/>
      <stop offset="100%" stop-color="#22d3ee"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="#06090f"/>
  <rect x="0" y="0" width="1200" height="630" fill="url(#g)" opacity="0.04"/>
  <text x="600" y="280" font-family="Inter,system-ui,sans-serif" font-size="80"
        font-weight="800" fill="url(#g)" text-anchor="middle">Recalium</text>
  <text x="600" y="360" font-family="Inter,system-ui,sans-serif" font-size="32"
        fill="#475569" text-anchor="middle">Your AI memory. Portable. Private. Yours.</text>
</svg>`;

  await sharp(Buffer.from(ogSvg)).png().toFile(join(publicDir, 'og/default.png'));

  console.log('Assets generated.');
} catch (err) {
  console.error('Asset generation failed:', err);
  process.exit(1);
}
