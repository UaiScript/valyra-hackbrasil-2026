/*
 * Geometria do gráfico em leque das previsões (ADR-0016). Só desenho: os números chegam
 * prontos da API como texto decimal e Number() aqui serve apenas para posicionar no SVG.
 */

export type FanInput = {
  history: { day: string; value: string }[];
  fan: { day: string; band: { p2_5: string; p10: string; p50: string; p90: string; p97_5: string } }[];
};

export type FanGeometry = {
  width: number;
  height: number;
  history: string;
  median: string;
  band80: string;
  band95: string;
  /** X do último ponto observado: divide passado e futuro. */
  nowX: number;
  ticks: { y: number; label: string }[];
  min: number;
  max: number;
};

const PAD = { top: 12, right: 12, bottom: 18, left: 40 };

function niceStep(range: number): number {
  const raw = range / 4;
  const power = 10 ** Math.floor(Math.log10(raw || 1));
  const unit = raw / power;
  return (unit <= 1 ? 1 : unit <= 2 ? 2 : unit <= 5 ? 5 : 10) * power;
}

function decimals(step: number): number {
  return step >= 1 ? 0 : Math.min(3, Math.ceil(-Math.log10(step)));
}

export function fanGeometry(input: FanInput, width = 640, height = 240): FanGeometry {
  const hist = input.history.map((p) => Number(p.value));
  const fan = input.fan.map((p) => ({
    lo95: Number(p.band.p2_5), lo80: Number(p.band.p10), mid: Number(p.band.p50), hi80: Number(p.band.p90), hi95: Number(p.band.p97_5),
  }));
  const all = [...hist, ...fan.flatMap((p) => [p.lo95, p.hi95])];
  let min = Math.min(...all);
  let max = Math.max(...all);
  if (!Number.isFinite(min) || !Number.isFinite(max)) { min = 0; max = 1; }
  if (max - min < 1e-9) { min -= 1; max += 1; }
  const step = niceStep(max - min);
  min = Math.floor(min / step) * step;
  max = Math.ceil(max / step) * step;

  const count = hist.length + fan.length;
  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (count <= 1 ? 0 : (i / (count - 1)) * innerW);
  const y = (v: number) => PAD.top + (1 - (v - min) / (max - min)) * innerH;
  const fmt = (n: number) => n.toFixed(1);
  const line = (pts: [number, number][]) => pts.map(([px, py], i) => `${i ? 'L' : 'M'}${fmt(px)},${fmt(py)}`).join('');

  const last = hist.length - 1;
  const anchor: [number, number] = [x(last), y(hist[last] ?? 0)];
  const fanX = (i: number) => x(hist.length + i);
  const area = (lo: (p: (typeof fan)[number]) => number, hi: (p: (typeof fan)[number]) => number) => {
    const top: [number, number][] = [anchor, ...fan.map((p, i) => [fanX(i), y(hi(p))] as [number, number])];
    const bottom: [number, number][] = fan.map((p, i) => [fanX(i), y(lo(p))] as [number, number]).reverse();
    return `${line([...top, ...bottom])}Z`;
  };

  const ticks: { y: number; label: string }[] = [];
  const places = decimals(step);
  for (let v = min; v <= max + step / 2; v += step) {
    ticks.push({ y: y(v), label: v.toFixed(places).replace('.', ',') });
  }

  return {
    width,
    height,
    history: line(hist.map((v, i) => [x(i), y(v)])),
    median: line([anchor, ...fan.map((p, i) => [fanX(i), y(p.mid)] as [number, number])]),
    band80: area((p) => p.lo80, (p) => p.hi80),
    band95: area((p) => p.lo95, (p) => p.hi95),
    nowX: anchor[0],
    ticks,
    min,
    max,
  };
}
