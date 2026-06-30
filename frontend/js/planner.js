/* SafeCycle - planner image generator.
   Renders a designed planner card (date / action / status) to a PNG using
   the Canvas API and triggers a browser download. Colors and typography
   come from the live CSS custom properties on :root, so the image always
   matches whatever theme the app is currently running.

   Pure rendering only -- no DOM mutation other than the temporary <a> tag
   used to trigger the download. */

const W = 720; // logical width
const H = 1000; // logical height
const PAD = 40;

const STATUS_LABELS = {
  ok: "Likely protected",
  warn: "Use backup",
  danger: "Seek medical help",
};

/** Read a CSS custom property off :root with a sensible fallback so the
 *  generator still works if tokens.css fails to load. */
function token(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/** Word-wrap `text` into lines no wider than `maxWidth` for the current ctx font. */
function wrapLines(ctx, text, maxWidth) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let line = "";
  for (const w of words) {
    const candidate = line ? `${line} ${w}` : w;
    if (ctx.measureText(candidate).width <= maxWidth) {
      line = candidate;
    } else {
      if (line) lines.push(line);
      line = w;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** Trigger a PNG download of the canvas with `filename`. */
function downloadCanvas(canvas, filename) {
  canvas.toBlob((blob) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Release the blob URL on the next tick; immediate revoke can race
    // some browsers' download dispatcher.
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }, "image/png");
}

/**
 * Render a planner image for a guidance result + timeline rows.
 *
 * @param {object} args
 * @param {string} args.product      Product name (e.g. "Yasmin").
 * @param {object} args.result       The adapted GuidanceResponse from api.js.
 * @param {Array}  args.timeline     Rows of { day, date, action, ok? }.
 * @param {string} [args.filename]   Override the download filename.
 */
export function downloadPlanner({ product, result, timeline, filename }) {
  const bg = token("--color-bg", "#fffaf9");
  const surface = token("--color-surface", "#ffffff");
  const surfaceAlt = token("--color-surface-alt", "#f4eded");
  const border = token("--color-border", "#e0cfcf");
  const primary = token("--color-primary", "#d48c8c");
  const primaryStrong = token("--color-primary-strong", "#c47374");
  const primarySoft = token("--color-primary-soft", "#f8eaea");
  const text = token("--color-text", "#3d2f2f");
  const muted = token("--color-text-muted", "#7a6666");
  const subtle = token("--color-text-subtle", "#a38a8a");

  // Per-status badge palette, matching tokens.css.
  const status = result.status || "warn";
  const statusFg = token(`--color-${status}`, primaryStrong);
  const statusBg = token(`--color-${status}-bg`, primarySoft);
  const statusLabel = STATUS_LABELS[status] || result.statusLabel || "Your guidance";

  // High-DPI: scale the bitmap, keep the logical drawing units the same.
  const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
  const canvas = document.createElement("canvas");
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  // Background.
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Outer rounded card so the planner reads like a single piece, not a sheet.
  ctx.fillStyle = surface;
  ctx.strokeStyle = border;
  ctx.lineWidth = 1;
  roundRect(ctx, PAD, PAD, W - PAD * 2, H - PAD * 2, 24, true, true);

  let y = PAD + 32;

  // Wordmark.
  ctx.fillStyle = primaryStrong;
  ctx.font = `700 28px Outfit, system-ui, sans-serif`;
  ctx.textBaseline = "top";
  ctx.fillText("SafeCycle", PAD + 28, y);

  // Subhead.
  ctx.fillStyle = muted;
  ctx.font = `500 14px Inter, system-ui, sans-serif`;
  ctx.fillText("Your personalised planner", PAD + 28, y + 36);

  y += 80;

  // Status pill.
  const pillX = PAD + 28;
  ctx.font = `600 14px Inter, system-ui, sans-serif`;
  const pillTextW = ctx.measureText(statusLabel).width;
  const pillW = pillTextW + 36;
  const pillH = 32;
  ctx.fillStyle = statusBg;
  roundRect(ctx, pillX, y, pillW, pillH, pillH / 2, true, false);
  ctx.fillStyle = statusFg;
  ctx.textBaseline = "middle";
  ctx.fillText(statusLabel, pillX + 18, y + pillH / 2 + 1);
  ctx.textBaseline = "top";

  y += pillH + 18;

  // Headline.
  ctx.fillStyle = text;
  ctx.font = `600 22px Outfit, system-ui, sans-serif`;
  const headlineLines = wrapLines(ctx, result.headline || "Your guidance", W - PAD * 2 - 56);
  for (const line of headlineLines) {
    ctx.fillText(line, PAD + 28, y);
    y += 30;
  }

  // Product line.
  if (product) {
    ctx.fillStyle = subtle;
    ctx.font = `500 14px Inter, system-ui, sans-serif`;
    ctx.fillText(`Method: ${product}`, PAD + 28, y + 4);
    y += 28;
  }

  y += 8;

  // Divider.
  ctx.strokeStyle = border;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD + 28, y);
  ctx.lineTo(W - PAD - 28, y);
  ctx.stroke();
  y += 24;

  // "Your timeline" section header.
  ctx.fillStyle = text;
  ctx.font = `600 16px Outfit, system-ui, sans-serif`;
  ctx.fillText("Your timeline", PAD + 28, y);
  y += 30;

  // Timeline rows.
  const rowH = 78;
  const rowGap = 12;
  const rowX = PAD + 28;
  const rowW = W - PAD * 2 - 56;
  for (const row of timeline) {
    // Row card.
    ctx.fillStyle = row.ok ? token("--color-ok-bg", "#f0f7f4") : surfaceAlt;
    roundRect(ctx, rowX, y, rowW, rowH, 14, true, false);

    // Accent stripe.
    ctx.fillStyle = row.ok ? token("--color-ok", "#4a6b5d") : primary;
    roundRect(ctx, rowX, y, 4, rowH, 2, true, false);

    // Day / date.
    ctx.fillStyle = text;
    ctx.font = `700 14px Outfit, system-ui, sans-serif`;
    ctx.fillText(row.day || "", rowX + 18, y + 14);
    ctx.fillStyle = subtle;
    ctx.font = `500 12px Inter, system-ui, sans-serif`;
    if (row.date) ctx.fillText(row.date, rowX + 18, y + 34);

    // Action (wrapped).
    ctx.fillStyle = text;
    ctx.font = `500 14px Inter, system-ui, sans-serif`;
    const actionLines = wrapLines(ctx, row.action || "", rowW - 140);
    let ay = y + 14;
    for (const line of actionLines.slice(0, 3)) {
      ctx.fillText(line, rowX + 124, ay);
      ay += 18;
    }

    y += rowH + rowGap;
  }

  // Footer disclaimer.
  const footerY = H - PAD - 56;
  ctx.fillStyle = subtle;
  ctx.font = `400 11px Inter, system-ui, sans-serif`;
  const disclaimerLines = wrapLines(
    ctx,
    result.disclaimer ||
      "This is general information based on common contraceptive guidance — not a diagnosis, prescription, or medical advice.",
    W - PAD * 2 - 56
  );
  let dy = footerY;
  for (const line of disclaimerLines.slice(0, 3)) {
    ctx.fillText(line, PAD + 28, dy);
    dy += 14;
  }

  downloadCanvas(canvas, filename || `safecycle-planner.png`);
}

/** Draw a rounded rectangle (no native Canvas helper everywhere). */
function roundRect(ctx, x, y, w, h, r, fill, stroke) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.lineTo(x + w - rr, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + rr);
  ctx.lineTo(x + w, y + h - rr);
  ctx.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
  ctx.lineTo(x + rr, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - rr);
  ctx.lineTo(x, y + rr);
  ctx.quadraticCurveTo(x, y, x + rr, y);
  ctx.closePath();
  if (fill) ctx.fill();
  if (stroke) ctx.stroke();
}
