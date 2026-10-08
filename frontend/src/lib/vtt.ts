/* WebVTT parsing for the transcript panel. Small on purpose: cues, timings, text. */

export interface Cue {
  start: number;
  end: number;
  text: string;
}

const TIMING =
  /(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{3})/;
const TAG = /<[^>]+>/g;

function seconds(hours: string | undefined, minutes: string, secs: string, millis: string) {
  const h = hours ? Number(hours.replace(":", "")) : 0;
  return h * 3600 + Number(minutes) * 60 + Number(secs) + Number(millis) / 1000;
}

export function parseVtt(text: string): Cue[] {
  const cues: Cue[] = [];
  let current: Cue | null = null;
  const body = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  for (const raw of body.split(/\r?\n/)) {
    const line = raw.trim();
    const timing = TIMING.exec(line);
    if (timing) {
      current = {
        start: seconds(timing[1], timing[2] ?? "0", timing[3] ?? "0", timing[4] ?? "0"),
        end: seconds(timing[5], timing[6] ?? "0", timing[7] ?? "0", timing[8] ?? "0"),
        text: "",
      };
      cues.push(current);
    } else if (!line) {
      current = null;
    } else if (current && !/^(WEBVTT|NOTE|STYLE|REGION)/.test(line)) {
      const clean = line.replace(TAG, "");
      current.text = current.text ? `${current.text} ${clean}` : clean;
    }
  }
  return cues.filter((cue) => cue.text.length > 0);
}

/** Index of the cue playing at `time`, or -1 between cues. */
export function cueIndexAt(cues: readonly Cue[], time: number): number {
  let lo = 0;
  let hi = cues.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const cue = cues[mid];
    if (!cue) break;
    if (time < cue.start) hi = mid - 1;
    else if (time >= cue.end) lo = mid + 1;
    else return mid;
  }
  return -1;
}

export function formatClock(totalSeconds: number): string {
  const whole = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(whole / 3600);
  const m = Math.floor((whole % 3600) / 60);
  const s = whole % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  return `${h > 0 ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}
