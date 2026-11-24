#!/usr/bin/env python3
"""Transforma o calendário de contribuições do GitHub em um eletroencefalograma.

Cada dia da semana vira um canal (Fp1, Fp2, C3, Cz, C4, O1, O2); cada semana é
um trecho de onda cuja amplitude cresce com o nº de contribuições do dia.
Usa só a stdlib. Dados reais via GraphQL (GITHUB_TOKEN). `--demo` existe apenas
para testar o layout localmente e nunca deve ser commitado.
"""
import json, math, os, random, sys, urllib.request

LOGIN = os.environ.get("GH_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Brunohgc9"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
CHANNELS = ["Fp1", "Fp2", "C3", "Cz", "C4", "O1", "O2"]  # domingo..sábado
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
THEMES = {
    "dark": dict(bg1="#0e130d", bg2="#171e15", ink="#F6F1E4", muted="#97a38d", gold="#E0B02A",
                 line="#2b3527", sig="#7EE0A8", card="#141a12"),
    "light": dict(bg1="#F6F1E4", bg2="#EDE5CF", ink="#1b261c", muted="#5b6955", gold="#B9860F",
                  line="#d6cdb0", sig="#1f8f5f", card="#FBF8EF"),
}
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "eeg-profile"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        raise RuntimeError(data.get("errors") or "usuário não encontrado")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]


def demo():
    rnd = random.Random(1)
    weeks = [[rnd.choice((0, 0, 1, 3, 6, 11)) for _ in range(7)] for _ in range(53)]
    return sum(map(sum, weeks)), weeks


def render(theme, total, weeks):
    t = THEMES[theme]
    nweeks = len(weeks)
    W, ml, mr, top, ch_h = 1200, 90, 40, 96, 54
    H = top + ch_h * 7 + 56
    px_per_week = (W - ml - mr) / nweeks
    rnd = random.Random(42)
    paths = []
    for ch in range(7):
        y0 = top + ch_h * ch + ch_h / 2
        pts = []
        phase = ch * 1.3
        for w, days in enumerate(weeks):
            # semanas incompletas (primeira/última) têm menos de 7 dias
            c = days[ch] if ch < len(days) else 0
            amp = min(c, 12) / 12 * (ch_h * 0.46)
            steps = 6
            for s in range(steps):
                phase += 0.9 + rnd.uniform(-0.2, 0.2)
                v = (math.sin(phase) * 0.7 + math.sin(phase * 2.7) * 0.3 + rnd.uniform(-0.2, 0.2))
                base = v * (1.4 if c == 0 else amp + 1.4)
                x = ml + (w + s / steps) * px_per_week
                pts.append(f"{x:.1f},{y0 - base:.1f}")
        paths.append((y0, "M" + " L".join(pts)))
    rows = []
    for i, (y0, d) in enumerate(paths):
        rows.append(
            f'<text class="m" x="{ml-14}" y="{y0+4:.0f}" font-size="13" fill="{t["muted"]}" text-anchor="end">{CHANNELS[i]}</text>'
            f'<line x1="{ml}" y1="{y0:.0f}" x2="{W-mr}" y2="{y0:.0f}" stroke="{t["line"]}" stroke-width="1" stroke-dasharray="2 6"/>'
            f'<path class="tr" style="animation-delay:{i*0.25:.2f}s" d="{d}" fill="none" stroke="{t["sig"]}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
        )
    names = ["Brain activity, last 12 months", "Activité cérébrale, 12 derniers mois",
             "Activitas cerebri, duodecim menses", "Atividade cerebral, últimos 12 meses"]
    titles = "".join(
        f'<g class="lg{" f" if i == 0 else ""}" style="animation-delay:{i*5}s"><text class="t" x="{ml-14}" y="46" font-size="22" font-weight="700" fill="{t["ink"]}">{n}</text></g>'
        for i, n in enumerate(names))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribuições do último ano como eletroencefalograma">
<style>
  .t{{font-family:{SANS}}} .m{{font-family:{MONO}}}
  .tr{{stroke-dasharray:6000;animation:dr 5s ease-out backwards}}
  @keyframes dr{{from{{stroke-dashoffset:6000}}to{{stroke-dashoffset:0}}}}
  .lg{{opacity:0;animation:lg 20s linear infinite both}} .lg.f{{opacity:1}}
  @keyframes lg{{0%{{opacity:0}}2.5%{{opacity:1}}22.5%{{opacity:1}}25%{{opacity:0}}100%{{opacity:0}}}}
  @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="{t['card']}" stroke="{t['line']}" stroke-width="2"/>
{titles}
<text class="m" x="{ml-14}" y="70" font-size="14" fill="{t['muted']}">{total} · Fp1…O2 · 1 canal/dia da semana · amplitude = commits</text>
{chr(10).join(rows)}
<text class="m" x="{W-mr}" y="{H-18}" font-size="12" fill="{t['muted']}" text-anchor="end">gerado por GitHub Actions · scripts/eeg.py</text>
</svg>'''
    return svg


def main():
    if "--demo" in sys.argv:
        total, weeks = demo()
        out = "/tmp"
    else:
        try:
            total, weeks = fetch()
        except Exception as e:  # mantém os SVGs anteriores se a API falhar
            print("falha ao buscar contribuições:", e)
            sys.exit(0)
        out = OUT
    os.makedirs(out, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out, f"eeg-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, total, weeks))
    print("ok", total, "contribuições,", len(weeks), "semanas ->", out)


if __name__ == "__main__":
    main()
