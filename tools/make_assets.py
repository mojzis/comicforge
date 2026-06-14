"""Generate the seed character library as standalone, hand-editable SVG files.

Each character lives in characters/<name>/ as:
  base.svg              the body (shared canvas)
  <slot>-<variant>.svg  stackable overlays drawn in the SAME canvas coords
  character.yaml        manifest (canvas size, slots, defaults)

All variants share the character's local viewBox, so composing a character is
just: stack base + chosen overlays. Edit any .svg by hand and it Just Works.
"""
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent.parent
CHARS = ROOT / "characters"

# ---- palette ---------------------------------------------------------------
S      = "#21304a"   # ink / outline
SKIN   = "#f3c9a0"
HAIR   = "#6b4a2b"
SHIRT  = "#4c8bf5"
PANTS  = "#2f3a4f"
SHOE   = "#21304a"
DBLACK = "#23262e"   # collie black
DWHITE = "#f7f7f4"   # collie white
TONGUE = "#e8788a"
COLLAR = "#e0a33a"
NOSE   = "#21242b"
MOUTH  = "#7a2b38"


def write(name_dir: Path, fname: str, w: int, h: int, inner: str):
    name_dir.mkdir(parents=True, exist_ok=True)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
        f'{textwrap.indent(inner.strip(), "  ")}\n</svg>\n'
    )
    (name_dir / fname).write_text(svg, encoding="utf-8")


def manifest(name_dir: Path, text: str):
    (name_dir / "character.yaml").write_text(text.strip() + "\n", encoding="utf-8")


# ===========================================================================
# TOM  (kid) — local canvas 200 x 320
# ===========================================================================
TOM = CHARS / "tom"
TW, TH = 200, 320

write(TOM, "base.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
  <!-- legs -->
  <path d="M84 238 L80 300" fill="none" stroke="{PANTS}" stroke-width="17"/>
  <path d="M116 238 L120 300" fill="none" stroke="{PANTS}" stroke-width="17"/>
  <!-- shoes -->
  <path d="M68 303 Q80 313 93 305" fill="none" stroke="{SHOE}" stroke-width="12"/>
  <path d="M107 305 Q120 313 132 303" fill="none" stroke="{SHOE}" stroke-width="12"/>
  <!-- torso -->
  <path d="M72 160 Q100 150 128 160 L122 236 Q100 245 78 236 Z" fill="{SHIRT}"/>
  <!-- neck -->
  <path d="M100 140 L100 156" stroke="{SKIN}" stroke-width="18" stroke-linecap="butt"/>
  <!-- head -->
  <circle cx="100" cy="92" r="50" fill="{SKIN}"/>
  <!-- hair -->
  <path d="M51 92 Q48 42 100 42 Q152 42 149 92 Q140 64 100 62 Q60 64 51 92 Z"
        fill="{HAIR}" stroke="none"/>
</g>
""")

# faces (drawn on head centred ~100,92)
write(TOM, "face-neutral.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="4.5" stroke-linecap="round" fill="none">
  <circle cx="83" cy="90" r="4.6" fill="{S}" stroke="none"/>
  <circle cx="117" cy="90" r="4.6" fill="{S}" stroke="none"/>
  <path d="M88 114 Q100 120 112 114"/>
</g>
""")
write(TOM, "face-happy.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="4.5" stroke-linecap="round" fill="none">
  <path d="M77 90 Q83 84 89 90"/>
  <path d="M111 90 Q117 84 123 90"/>
  <path d="M83 112 Q100 132 117 112 Q100 119 83 112 Z" fill="{MOUTH}" stroke="{S}"/>
</g>
""")
write(TOM, "face-surprised.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="3" stroke-linecap="round" fill="none">
  <circle cx="83" cy="89" r="6.4" fill="#ffffff" stroke="{S}"/>
  <circle cx="83" cy="89" r="2.6" fill="{S}" stroke="none"/>
  <circle cx="117" cy="89" r="6.4" fill="#ffffff" stroke="{S}"/>
  <circle cx="117" cy="89" r="2.6" fill="{S}" stroke="none"/>
  <path d="M74 76 Q83 71 92 76" stroke-width="4"/>
  <path d="M108 76 Q117 71 126 76" stroke-width="4"/>
  <ellipse cx="100" cy="116" rx="7" ry="10" fill="{MOUTH}" stroke="{S}"/>
</g>
""")
write(TOM, "face-sad.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="4.5" stroke-linecap="round" fill="none">
  <circle cx="83" cy="92" r="4.4" fill="{S}" stroke="none"/>
  <circle cx="117" cy="92" r="4.4" fill="{S}" stroke="none"/>
  <path d="M75 80 Q84 84 91 82" stroke-width="4"/>
  <path d="M109 82 Q116 84 125 80" stroke-width="4"/>
  <path d="M88 119 Q100 110 112 119"/>
</g>
""")

# arms (shoulders ~ x76/x124, y160)
write(TOM, "arms-down.svg", TW, TH, f"""
<g fill="none" stroke="{SHIRT}" stroke-width="13" stroke-linecap="round">
  <path d="M76 168 Q63 200 70 230"/>
  <path d="M124 168 Q137 200 130 230"/>
</g>
<circle cx="70" cy="232" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<circle cx="130" cy="232" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
""")
write(TOM, "arms-wave.svg", TW, TH, f"""
<g fill="none" stroke="{SHIRT}" stroke-width="13" stroke-linecap="round">
  <path d="M76 168 Q63 200 70 230"/>
  <path d="M124 166 Q150 130 150 98"/>
</g>
<circle cx="70" cy="232" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<circle cx="150" cy="94" r="9" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
""")
write(TOM, "arms-point.svg", TW, TH, f"""
<g fill="none" stroke="{SHIRT}" stroke-width="13" stroke-linecap="round">
  <path d="M76 168 Q63 200 70 230"/>
  <path d="M124 174 Q152 162 182 158"/>
</g>
<circle cx="70" cy="232" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<circle cx="184" cy="158" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
""")

manifest(TOM, """
name: tom
label: Tom
viewbox: [200, 320]
default:
  face: neutral
  arms: down
slots:
  arms: [down, wave, point]
  face: [neutral, happy, surprised, sad]
""")

# ===========================================================================
# BÁRA  (border collie) — local canvas 240 x 180, facing right
# ===========================================================================
BARA = CHARS / "bara"
BW, BH = 240, 180

write(BARA, "base.svg", BW, BH, f"""
<g stroke="{S}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
  <!-- tail -->
  <path d="M42 104 Q14 96 24 66" fill="none" stroke="{DWHITE}" stroke-width="16"/>
  <!-- legs -->
  <path d="M78 134 L74 166" fill="none" stroke="{DWHITE}" stroke-width="13"/>
  <path d="M106 138 L104 168" fill="none" stroke="{DWHITE}" stroke-width="13"/>
  <path d="M150 138 L150 168" fill="none" stroke="{DWHITE}" stroke-width="13"/>
  <path d="M176 134 L180 166" fill="none" stroke="{DWHITE}" stroke-width="13"/>
  <!-- body -->
  <ellipse cx="112" cy="104" rx="76" ry="38" fill="{DWHITE}"/>
  <!-- head -->
  <circle cx="192" cy="92" r="33" fill="{DWHITE}"/>
  <!-- snout -->
  <path d="M214 90 Q236 95 231 108 Q223 117 208 112 Z" fill="{DWHITE}"/>
  <!-- ears -->
  <path d="M168 70 Q170 44 186 46 Q188 64 180 78 Z" fill="{DBLACK}" stroke="{S}"/>
  <path d="M198 66 Q210 46 222 54 Q220 72 208 80 Z" fill="{DBLACK}" stroke="{S}"/>
  <!-- black saddle: upper back only, leaves white belly + legs -->
  <path d="M60 104 Q70 74 116 70 Q164 74 174 104 Q150 110 112 110 Q74 110 60 104 Z"
        fill="{DBLACK}" stroke="none"/>
  <!-- black head patch (leaves white blaze + muzzle) -->
  <path d="M170 92 Q168 58 190 58 Q206 60 206 80 Q196 76 186 80 Q176 82 170 92 Z"
        fill="{DBLACK}" stroke="none"/>
  <!-- collar -->
  <path d="M166 104 Q184 118 204 104" fill="none" stroke="{COLLAR}" stroke-width="8"/>
  <circle cx="186" cy="116" r="4" fill="{COLLAR}" stroke="{S}" stroke-width="2"/>
</g>
""")

write(BARA, "face-neutral.svg", BW, BH, f"""
<g stroke="{S}" stroke-width="3.5" stroke-linecap="round" fill="none">
  <circle cx="198" cy="88" r="4.6" fill="{S}" stroke="none"/>
  <circle cx="199.6" cy="86.6" r="1.4" fill="#ffffff" stroke="none"/>
  <ellipse cx="230" cy="102" rx="6" ry="5" fill="{NOSE}" stroke="none"/>
  <path d="M214 110 Q222 116 230 110"/>
</g>
""")
write(BARA, "face-happy.svg", BW, BH, f"""
<g stroke="{S}" stroke-width="3.5" stroke-linecap="round" fill="none">
  <path d="M193 88 Q198 83 203 88"/>
  <ellipse cx="230" cy="102" rx="6" ry="5" fill="{NOSE}" stroke="none"/>
  <path d="M210 110 Q222 126 232 110 Z" fill="{MOUTH}" stroke="{S}"/>
  <path d="M219 116 Q223 132 229 117 Z" fill="{TONGUE}" stroke="{S}"/>
</g>
""")

manifest(BARA, """
name: bara
label: Bára
viewbox: [240, 180]
default:
  face: neutral
slots:
  face: [neutral, happy]
""")

print("wrote characters:", ", ".join(p.name for p in sorted(CHARS.iterdir())))
