"""Generate the seed character and scene library as standalone, hand-editable SVG files.

Characters are written into ``library/characters/<name>/``:
  base.svg              the body (shared canvas)
  <slot>-<variant>.svg  stackable overlays drawn in the SAME canvas coords
  character.yaml        manifest (canvas size, slots, defaults)

Scenes are written into ``projects/_scenes/<name>/``:
  base.svg              background base
  <slot>-<variant>.svg  weather / time-of-day overlays
  scene.yaml            manifest

All variants share the local viewBox of their asset, so composing is just:
stack base + chosen overlays.  Edit any .svg by hand and it Just Works.
"""
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent.parent
CHARS = ROOT / "library" / "characters"

# ---- palette ---------------------------------------------------------------
S       = "#21304a"   # ink / outline
SKIN    = "#f3c9a0"
SKIN_SH = "#d9a679"   # skin shadow
HAIR    = "#6b4a2b"
HAIR_HI = "#9c7142"   # hair highlight
SHIRT   = "#4c8bf5"
SHIRT_SH = "#3a6fcf"  # shirt shadow
PANTS   = "#2f3a4f"
SHOE    = "#21304a"
CHEEK   = "#ef9f8e"
DBLACK  = "#23262e"   # collie black
DWHITE  = "#f7f7f4"   # collie white
TONGUE  = "#e8788a"
COLLAR  = "#e0a33a"
NOSE    = "#21242b"
MOUTH   = "#7a2b38"

# scene palette
SKY      = "#bfe2f5"
SUN      = "#f4c945"
GRASS    = "#9ad06a"
GRASS2   = "#7cbb55"
WOOD     = "#a7702f"
COOP     = "#caa06a"
COOPROOF = "#8c4a2f"
COMB     = "#d9434f"
RAIN     = "#5a6b7a"
RAINLINE = "#dff1fb"
WALL     = "#efe6d2"
FLOOR    = "#c79a64"
RUG      = "#d8807a"
GLASS    = "#cfeaf4"
FRAME    = "#7a5230"


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


def scene_manifest(name_dir: Path, text: str):
    (name_dir / "scene.yaml").write_text(text.strip() + "\n", encoding="utf-8")


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
  <path d="M62 300 Q80 316 96 305 L94 296 Q80 303 70 296 Z" fill="{SHOE}" stroke-width="3"/>
  <path d="M104 305 Q120 316 138 300 L130 296 Q120 303 106 296 Z" fill="{SHOE}" stroke-width="3"/>
  <!-- torso -->
  <path d="M72 160 Q100 150 128 160 L122 236 Q100 245 78 236 Z" fill="{SHIRT}"/>
  <!-- shirt shading (right side) -->
  <path d="M100 154 L128 160 L122 236 Q111 241 100 240 Z"
        fill="{SHIRT_SH}" stroke="none"/>
  <!-- collar -->
  <path d="M86 157 Q100 167 114 157" fill="none" stroke="{S}" stroke-width="3"/>
  <!-- neck -->
  <path d="M100 138 L100 156" stroke="{SKIN}" stroke-width="18" stroke-linecap="butt"/>
  <path d="M104 138 L104 156" stroke="{SKIN_SH}" stroke-width="6" stroke-linecap="butt"/>
  <!-- ears -->
  <circle cx="52" cy="97" r="9" fill="{SKIN}"/>
  <circle cx="148" cy="97" r="9" fill="{SKIN}"/>
  <!-- head -->
  <circle cx="100" cy="92" r="50" fill="{SKIN}"/>
  <!-- hair -->
  <path d="M51 92 Q48 42 100 42 Q152 42 149 92 Q140 64 100 62 Q60 64 51 92 Z"
        fill="{HAIR}" stroke="none"/>
  <!-- hair highlight + cowlick -->
  <path d="M66 58 Q100 48 134 58" fill="none" stroke="{HAIR_HI}" stroke-width="4"/>
  <path d="M100 62 Q104 49 116 46" fill="none" stroke="{HAIR}" stroke-width="5"/>
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
  <ellipse cx="76" cy="105" rx="6" ry="4" fill="{CHEEK}" stroke="none"/>
  <ellipse cx="124" cy="105" rx="6" ry="4" fill="{CHEEK}" stroke="none"/>
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
  <path d="M79 100 Q77 106 81 110" stroke-width="3"/>
</g>
""")
write(TOM, "face-angry.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="4.5" stroke-linecap="round" fill="none">
  <path d="M75 83 L92 90" stroke-width="5"/>
  <path d="M125 83 L108 90" stroke-width="5"/>
  <circle cx="85" cy="95" r="4.4" fill="{S}" stroke="none"/>
  <circle cx="115" cy="95" r="4.4" fill="{S}" stroke="none"/>
  <path d="M86 119 Q100 111 114 119"/>
</g>
""")
write(TOM, "face-laugh.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="4.5" stroke-linecap="round" fill="none">
  <path d="M76 89 Q83 82 90 89"/>
  <path d="M110 89 Q117 82 124 89"/>
  <ellipse cx="74" cy="106" rx="6.5" ry="4.5" fill="{CHEEK}" stroke="none"/>
  <ellipse cx="126" cy="106" rx="6.5" ry="4.5" fill="{CHEEK}" stroke="none"/>
  <path d="M80 110 Q100 140 120 110 Q100 121 80 110 Z" fill="{MOUTH}" stroke="{S}"/>
  <path d="M92 123 Q100 131 108 123 Z" fill="{TONGUE}" stroke="none"/>
</g>
""")
write(TOM, "face-wink.svg", TW, TH, f"""
<g stroke="{S}" stroke-width="4.5" stroke-linecap="round" fill="none">
  <circle cx="83" cy="90" r="4.6" fill="{S}" stroke="none"/>
  <path d="M110 91 Q117 85 124 91"/>
  <ellipse cx="124" cy="104" rx="6" ry="4" fill="{CHEEK}" stroke="none"/>
  <path d="M85 113 Q101 126 116 112"/>
</g>
""")

# arms (shoulders ~ x76/x124, y160-170)
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
write(TOM, "arms-crossed.svg", TW, TH, f"""
<g fill="none" stroke="{SHIRT}" stroke-width="13" stroke-linecap="round">
  <path d="M76 170 Q92 196 126 202"/>
  <path d="M124 170 Q108 198 74 206"/>
</g>
<circle cx="128" cy="202" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<circle cx="72" cy="206" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
""")
write(TOM, "arms-hips.svg", TW, TH, f"""
<g fill="none" stroke="{SHIRT}" stroke-width="13" stroke-linecap="round">
  <path d="M76 170 Q58 192 80 206"/>
  <path d="M124 170 Q142 192 120 206"/>
</g>
<circle cx="82" cy="208" r="7.5" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<circle cx="118" cy="208" r="7.5" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
""")
write(TOM, "arms-thumbsup.svg", TW, TH, f"""
<g fill="none" stroke="{SHIRT}" stroke-width="13" stroke-linecap="round">
  <path d="M76 168 Q63 200 70 230"/>
  <path d="M124 168 Q142 150 138 122"/>
</g>
<circle cx="70" cy="232" r="8" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<circle cx="138" cy="118" r="10" fill="{SKIN}" stroke="{S}" stroke-width="4"/>
<path d="M138 110 L138 99" fill="none" stroke="{SKIN}" stroke-width="7"
      stroke-linecap="round"/>
<path d="M138 110 L138 99" fill="none" stroke="{S}" stroke-width="2"
      stroke-linecap="round"/>
""")

manifest(TOM, """
name: tom
label: Tom
viewbox: [200, 320]
default:
  face: neutral
  arms: down
slots:
  arms: [down, wave, point, crossed, hips, thumbsup]
  face: [neutral, happy, surprised, sad, angry, laugh, wink]
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

# ===========================================================================
# SCENES — backgrounds, same base + overlay model, scaled to *cover* a panel.
# ===========================================================================
SCENES = ROOT / "projects" / "_scenes"

# ---- dvur (farmyard) — canvas 320 x 200 -----------------------------------
DVUR = SCENES / "dvur"
SCW, SCH = 320, 200

write(DVUR, "base.svg", SCW, SCH, f"""
<!-- sky -->
<rect x="0" y="0" width="320" height="132" fill="{SKY}"/>
<circle cx="268" cy="42" r="26" fill="{SUN}"/>
<!-- rolling hills -->
<path d="M0 132 Q80 98 168 124 Q244 146 320 116 L320 132 Z" fill="{GRASS2}"/>
<!-- ground -->
<rect x="0" y="128" width="320" height="72" fill="{GRASS}"/>
<!-- fence -->
<g stroke="{WOOD}" stroke-width="6" stroke-linecap="round">
  <path d="M18 150 L18 180"/>
  <path d="M46 150 L46 180"/>
  <path d="M74 150 L74 180"/>
  <path d="M8 158 L84 158"/>
  <path d="M8 171 L84 171"/>
</g>
<!-- chicken coop -->
<rect x="212" y="122" width="80" height="56" fill="{COOP}" stroke="{S}" stroke-width="3"/>
<path d="M206 122 L252 96 L298 122 Z" fill="{COOPROOF}" stroke="{S}" stroke-width="3"/>
<rect x="240" y="142" width="24" height="36" fill="{WOOD}" stroke="{S}" stroke-width="3"/>
<circle cx="246" cy="160" r="2.5" fill="{S}"/>
<!-- a chicken -->
<g stroke="{S}" stroke-width="2.5">
  <ellipse cx="122" cy="168" rx="14" ry="11" fill="#ffffff"/>
  <circle cx="135" cy="158" r="7" fill="#ffffff"/>
  <path d="M132 151 Q134 146 137 150 Q139 146 141 151" fill="{COMB}" stroke="none"/>
  <path d="M141 159 L149 161 L141 163 Z" fill="{SUN}" stroke="none"/>
  <circle cx="137" cy="158" r="1.4" fill="{S}" stroke="none"/>
  <path d="M117 178 L115 184 M126 178 L126 184" stroke="{SUN}"/>
</g>
""")
write(DVUR, "weather-clear.svg", SCW, SCH, """
<!-- clear skies: no overlay -->
""")
write(DVUR, "weather-rain.svg", SCW, SCH, f"""
<rect x="0" y="0" width="320" height="200" fill="{RAIN}" opacity="0.26"/>
<g stroke="{RAINLINE}" stroke-width="2.2" stroke-linecap="round" opacity="0.75">
  <path d="M40 60 L33 80"/>
  <path d="M78 48 L71 68"/>
  <path d="M120 64 L113 84"/>
  <path d="M164 52 L157 72"/>
  <path d="M206 66 L199 86"/>
  <path d="M250 54 L243 74"/>
  <path d="M292 64 L285 84"/>
</g>
<g fill="#eef3f7" stroke="{S}" stroke-width="2.5">
  <ellipse cx="92" cy="34" rx="34" ry="15"/>
  <ellipse cx="62" cy="40" rx="22" ry="12"/>
  <ellipse cx="120" cy="42" rx="20" ry="11"/>
</g>
""")
scene_manifest(DVUR, """
name: dvur
label: Dvůr
viewbox: [320, 200]
default:
  weather: clear
slots:
  weather: [clear, rain]
""")

# ---- pokoj (room) — canvas 320 x 200, no slots -----------------------------
POKOJ = SCENES / "pokoj"

write(POKOJ, "base.svg", SCW, SCH, f"""
<!-- wall + floor -->
<rect x="0" y="0" width="320" height="150" fill="{WALL}"/>
<rect x="0" y="146" width="320" height="54" fill="{FLOOR}"/>
<path d="M0 146 L320 146" stroke="{S}" stroke-width="2"/>
<!-- window onto a sunny sky -->
<rect x="30" y="34" width="92" height="74" fill="{GLASS}" stroke="{FRAME}" stroke-width="6"/>
<path d="M76 34 L76 108 M30 71 L122 71" stroke="{FRAME}" stroke-width="5"/>
<circle cx="102" cy="52" r="10" fill="{SUN}"/>
<!-- framed landscape -->
<rect x="206" y="40" width="66" height="50" fill="#fdf7e8" stroke="{FRAME}" stroke-width="5"/>
<path d="M212 78 L232 58 L246 72 L256 60 L264 78 Z" fill="{GRASS}" stroke="none"/>
<circle cx="252" cy="52" r="6" fill="{SUN}"/>
<!-- rug -->
<ellipse cx="160" cy="176" rx="118" ry="17" fill="{RUG}" stroke="{S}" stroke-width="2"/>
""")
scene_manifest(POKOJ, """
name: pokoj
label: Pokoj
viewbox: [320, 200]
""")

print("wrote library/characters:", ", ".join(p.name for p in sorted(CHARS.iterdir())))
print("wrote projects/_scenes:", ", ".join(p.name for p in sorted(SCENES.iterdir())))
