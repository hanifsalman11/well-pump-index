import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/well-pump-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2").strip()
CUSTOM_WELL = os.environ.get("CUSTOM_WELL", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_wells.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Pump Model / Well Depth Scenario, Pumping Depth Ft, Target GPM, Motor HP, System PSI, Tank Total Gal)
SEED_WELLS = [
    ("Goulds 10GS07412 3/4 HP 10 GPM 4-Inch Submersible", 180, 10, 0.75, "40/60 PSI", 44),
    ("Goulds 10GS10412 1.0 HP 10 GPM Deep Well Pump", 260, 10, 1.0, "40/60 PSI", 44),
    ("Goulds 18GS15412 1.5 HP 18 GPM High-Flow Well Pump", 220, 18, 1.5, "40/60 PSI", 86),
    ("Grundfos 10SQ07-240 3/4 HP 3-Inch Constant Speed", 200, 10, 0.75, "40/60 PSI", 44),
    ("Grundfos Scala2 & SQE 10SQE10-290 Constant Pressure", 250, 10, 1.0, "50 PSI Constant", 20),
    ("Franklin Electric J-Class 1/2 HP 10 GPM Submersible", 120, 10, 0.5, "30/50 PSI", 32),
    ("Franklin Electric Schaefer 1.0 HP 15 GPM 230V Pump", 200, 15, 1.0, "40/60 PSI", 62),
    ("Pentair Flotec FP2222 3/4 HP 10 GPM 230V 3-Wire", 175, 10, 0.75, "40/60 PSI", 44),
    ("Pentair Sta-Rite 10DOM05221 1/2 HP 10 GPM Submersible", 110, 10, 0.5, "30/50 PSI", 32),
    ("Red Lion RL12G07-2W2V 3/4 HP 12 GPM 2-Wire 230V", 160, 12, 0.75, "40/60 PSI", 44),
    ("Red Lion RL12G10-3W2V 1.0 HP 12 GPM 3-Wire w/ Box", 240, 12, 1.0, "40/60 PSI", 44),
    ("Amtrol Well-X-Trol WX-202 (20 Gallon) Pressure Tank", 120, 7, 0.5, "30/50 PSI", 20),
    ("Amtrol Well-X-Trol WX-205 (34 Gallon) Pressure Tank", 160, 10, 0.75, "40/60 PSI", 34),
    ("Amtrol Well-X-Trol WX-250 (44 Gallon) Pressure Tank", 200, 12, 1.0, "40/60 PSI", 44),
    ("Amtrol Well-X-Trol WX-252 (62 Gallon) Pressure Tank", 220, 16, 1.5, "40/60 PSI", 62),
    ("Water Worker HT-44B (44 Gallon) Vertical Well Tank", 180, 12, 0.75, "40/60 PSI", 44),
    ("Water Worker HT-86B (86 Gallon) Large Well Tank", 250, 20, 1.5, "40/60 PSI", 86),
    ("Hallmark Industries MA0414X-7A 1.0 HP 230V Stainless", 200, 13, 1.0, "40/60 PSI", 44),
    ("VEVOR 1.5 HP 37 GPM 230V Stainless Deep Well Pump", 220, 18, 1.5, "40/60 PSI", 86),
    ("100-Foot Shallow Rock Well (3-Bedroom Home)", 100, 10, 0.5, "40/60 PSI", 44),
    ("150-Foot Residential Deep Well (4-Bedroom Home)", 150, 12, 0.75, "40/60 PSI", 44),
    ("200-Foot Deep Well Submersible Pump & Wire Setup", 200, 10, 0.75, "40/60 PSI", 44),
    ("250-Foot Deep Well Submersible Pump & Wire Setup", 250, 10, 1.0, "40/60 PSI", 44),
    ("300-Foot Deep Well Submersible Pump & Wire Setup", 300, 10, 1.5, "40/60 PSI", 44),
    ("400-Foot Deep Agricultural & Homestead Well Setup", 400, 10, 2.0, "40/60 PSI", 44),
    ("500-Foot Ultra-Deep Bedrock Well Pump Setup", 500, 7, 2.0, "40/60 PSI", 34),
    ("1/2 HP Convertible Deep Well Jet Pump (25–80 Ft)", 65, 8, 0.5, "30/50 PSI", 32),
    ("1.0 HP Cast Iron Shallow/Deep Well Jet Pump", 80, 10, 1.0, "30/50 PSI", 44),
    ("Cycle Stop Valve CSV1A Constant Pressure Well System", 180, 12, 1.0, "50 PSI Constant", 20),
    ("Off-Grid 24V/48V Solar DC Submersible Well Pump", 160, 6, 0.75, "Cistern / 40 PSI", 34)
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=200.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_well_queries():
    """Mengambil kueri ukuran pompa sumur bor & tangki tekan dari Google Autocomplete US."""
    discovered = []
    seeds = [
        "what size well pump for ",
        "well pressure tank size for ",
        "submersible well pump wire size for ",
        "well x trol "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        ft_match = re.search(r"(\d{2,3})\s*(?:ft|foot|feet)", cleaned)
                        depth_val = int(ft_match.group(1)) if ft_match else 200
                        hp_val = 0.5 if depth_val <= 120 else (0.75 if depth_val <= 200 else (1.0 if depth_val <= 280 else 1.5))
                        discovered.append((cleaned.title(), depth_val, 10, hp_val, "40/60 PSI", 44))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_well_data(well_tuple):
    """Mesin Fisika Hidrolik TDH Sumur Bor & Franklin Electric Wire Chart (100% bebas gagal)."""
    item_name, depth_ft, gpm, hp, psi_setting, tank_gal = well_tuple

    # Rumus Total Dynamic Head (TDH in Feet):
    # 1. Pumping Water Level = depth_ft
    # 2. Discharge Pressure Head: 50 PSI average * 2.31 ft/PSI = 115.5 ft
    # 3. Pipe Friction Loss (~6 ft per 100 ft of 1.25" poly drop pipe)
    avg_psi = 40 if "30/50" in psi_setting else 50
    pressure_head_ft = round(avg_psi * 2.31, 1)
    friction_loss_ft = round((depth_ft + 50) * 0.06, 1)
    total_tdh_ft = int(round(depth_ft + pressure_head_ft + friction_loss_ft))

    # Drawdown factor: 30/50 PSI = 0.31 | 40/60 PSI = 0.27
    dd_factor = 0.31 if "30/50" in psi_setting else 0.27
    usable_drawdown_gal = round(tank_gal * dd_factor, 1)
    precharge_psi = 28 if "30/50" in psi_setting else 38

    # Franklin Electric AIM 230V Copper Wire Gauge Sizing based on HP and Total Cable Length (Depth + 50 ft to panel)
    cable_run_ft = depth_ft + 50
    if hp <= 0.75:
        wire_awg = "12 AWG Submersible Copper" if cable_run_ft <= 300 else "10 AWG Submersible Copper"
    elif hp <= 1.0:
        wire_awg = "12 AWG Submersible Copper" if cable_run_ft <= 250 else "10 AWG Submersible Copper"
    else:
        wire_awg = "10 AWG Submersible Copper" if cable_run_ft <= 280 else "8 AWG Submersible Copper"

    return {
        "well_name": item_name,
        "seo_title": f"{item_name} TDH, Pressure Tank & Wire Size Calculator (2026)",
        "meta_description": f"Calculate exact Total Dynamic Head ({total_tdh_ft} ft TDH), pressure tank drawdown ({usable_drawdown_gal} gal on {tank_gal}-gal tank), and 230V submersible wire gauge ({wire_awg}) for {item_name}.",
        "specs": {
            "pumping_depth_ft": depth_ft,
            "total_tdh_ft": total_tdh_ft,
            "flow_rate_gpm": gpm,
            "recommended_hp": hp,
            "pressure_switch_psi": psi_setting,
            "tank_precharge_psi": precharge_psi,
            "recommended_tank_gal": tank_gal,
            "usable_drawdown_gal": usable_drawdown_gal,
            "recommended_wire_awg": wire_awg
        },
        "hydraulic_verdict": f"At a {depth_ft}-foot pumping water depth plus {pressure_head_ft} ft of household pressure head ({psi_setting}) and {friction_loss_ft} ft of friction loss, {item_name} operates against {total_tdh_ft} feet of Total Dynamic Head (TDH). To deliver {gpm} GPM with a minimum 60-second motor cooling cycle, pair a {hp} HP 230V submersible pump with a {tank_gal}-gallon diaphragm pressure tank ({usable_drawdown_gal} gal usable drawdown, pre-charged to {precharge_psi} PSI) and {wire_awg} cable.",
        "hardware_bundle": [
            {
                "badge": f"{hp} HP / {gpm} GPM Pump",
                "title": f"{hp} HP {gpm} GPM 230V 4-Inch Stainless Steel Submersible Deep Well Pump",
                "price_range": "$249 - $799",
                "amazon_query": f"{hp} HP {gpm} GPM 230V 4 Inch Stainless Submersible Deep Well Pump",
                "well_note": f"Engineered withhermetically sealed stainless steel impellers and built-in check valve to overcome {total_tdh_ft} ft of Total Dynamic Head."
            },
            {
                "badge": f"{tank_gal}-Gal Pressure Tank",
                "title": f"{tank_gal}-Gallon Pre-Charged Vertical Diaphragm Well Pressure Tank ({usable_drawdown_gal} Gal Drawdown)",
                "price_range": "$229 - $599",
                "amazon_query": f"{tank_gal} Gallon Well Pressure Tank Diaphragm Vertical",
                "well_note": f"Stores {usable_drawdown_gal} gallons of pressurized water between {psi_setting} cycles so the submersible motor runs at least 1 full minute per start."
            },
            {
                "badge": "Franklin AIM Submersible Wire",
                "title": f"{cable_run_ft}ft Twisted/Flat Jacketed {wire_awg} 3-Wire + Ground Submersible Pump Cable",
                "price_range": "$139 - $489",
                "amazon_query": f"{wire_awg} Submersible Well Pump Wire 3 Wire With Ground",
                "well_note": f"Sized per Franklin Electric AIM tables to keep voltage drop below 5% over a {cable_run_ft} ft submerged run."
            },
            {
                "badge": "Brass Tank Tee & Switch Kit",
                "title": f"11-Inch Solid Lead-Free Brass Tank Tee Kit + Square D {psi_setting} Low-Pressure Cut-Off Switch",
                "price_range": "$59 - $129",
                "amazon_query": "Brass Well Tank Tee Kit Square D 40/60 Pressure Switch",
                "well_note": "Includes 100 PSI pressure gauge, 75 PSI brass pressure relief valve, boiler drain, and dry-run protection switch."
            }
        ],
        "installation_checklist": [
            f"Set your empty pressure tank's Schrader air valve to exactly 2 PSI below the pressure switch cut-in setting ({precharge_psi} PSI for a {psi_setting} switch) BEFORE turning on the pump.",
            "Install a secondary inline spring-loaded Solid Brass Check Valve every 200 feet of drop pipe (plus one at the pump discharge) to prevent water hammer and backspin.",
            "Clamp a rubber Two-Piece Torque Arrestor just above the submersible pump and use waterproof heat-shrink butt splice kits on all submerged wire joints.",
            "Never install a check valve between the well pressure tank and the pressure switch tee; doing so traps pressure and causes rapid motor-destroying short-cycling."
        ],
        "faqs": [
            {
                "q": f"How do I calculate Total Dynamic Head (TDH) for {item_name}?",
                "a": f"Add your pumping water depth ({depth_ft} ft), vertical elevation to the pressure tank, pipe friction loss (~{friction_loss_ft} ft), and household operating pressure multiplied by 2.31 ({avg_psi} PSI × 2.31 = {pressure_head_ft} ft). That gives a Total Dynamic Head of {total_tdh_ft} feet."
            },
            {
                "q": f"What size pressure tank do I need for a {gpm} GPM well pump?",
                "a": f"To guarantee a minimum 1-minute pump run time ({gpm} gallons of usable drawdown), divide {gpm} GPM by the {psi_setting} drawdown factor ({dd_factor}). That requires at least a {tank_gal}-gallon total volume diaphragm tank providing {usable_drawdown_gal} gallons of drawdown."
            },
            {
                "q": f"What air pressure should be in my well tank for a {psi_setting} switch?",
                "a": f"With all water drained from the tank and zero water pressure on the gauge, inflate the top Schrader air valve to {precharge_psi} PSI (2 PSI below the {'30' if precharge_psi == 28 else '40'} PSI cut-in pressure)."
            }
        ]
    }


def generate_well_data(well_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic TDH & Franklin Wire Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_well_data(well_tuple)

    item_name, depth_ft, gpm, hp, psi_setting, tank_gal = well_tuple
    avg_psi = 40 if "30/50" in psi_setting else 50
    total_tdh_ft = int(round(depth_ft + (avg_psi * 2.31) + ((depth_ft + 50) * 0.06)))
    dd_factor = 0.31 if "30/50" in psi_setting else 0.27
    usable_dd = round(tank_gal * dd_factor, 1)
    precharge_psi = 28 if "30/50" in psi_setting else 38

    prompt = f"""
You are a National Ground Water Association (NGWA) Certified Master Well Driller & Pump Installer. Create an accurate 2026 Total Dynamic Head (TDH), pressure tank drawdown, and submersible wire sizing guide for: "{item_name}".
Baseline reference specs: Pumping Depth={depth_ft} ft, Total Dynamic Head={total_tdh_ft} ft, Flow={gpm} GPM, Pump={hp} HP, Switch={psi_setting} (Pre-charge {precharge_psi} PSI), Tank={tank_gal} Gal ({usable_dd} Gal Drawdown).
Return ONLY a valid JSON object matching this exact schema:
{{
  "well_name": "{item_name}",
  "seo_title": "{item_name} TDH, Pressure Tank & Wire Size Calculator (2026)",
  "meta_description": "Calculate exact Total Dynamic Head (TDH), pressure tank drawdown gallons, and 230V submersible copper wire gauge for {item_name}.",
  "specs": {{
    "pumping_depth_ft": {depth_ft},
    "total_tdh_ft": {total_tdh_ft},
    "flow_rate_gpm": {gpm},
    "recommended_hp": {hp},
    "pressure_switch_psi": "{psi_setting}",
    "tank_precharge_psi": {precharge_psi},
    "recommended_tank_gal": {tank_gal},
    "usable_drawdown_gal": {usable_dd},
    "recommended_wire_awg": "12 AWG or 10 AWG Submersible Copper"
  }},
  "hydraulic_verdict": "3-sentence technical summary stating pumping depth, pressure head in feet (PSI x 2.31), Total Dynamic Head (TDH), tank drawdown gallons, and submersible wire gauge.",
  "hardware_bundle": [
    {{
      "badge": "Submersible Well Pump",
      "title": "Exact HP and GPM 4-Inch Stainless Submersible Deep Well Pump recommendation",
      "price_range": "$259 - $799",
      "amazon_query": "{hp} HP {gpm} GPM 230V Stainless Submersible Deep Well Pump",
      "well_note": "1-sentence TDH and stainless impeller note"
    }},
    {{
      "badge": "Diaphragm Pressure Tank",
      "title": "Exact Gallon Pre-Charged Vertical Well Pressure Tank recommendation",
      "price_range": "$229 - $599",
      "amazon_query": "{tank_gal} Gallon Well Pressure Tank Vertical",
      "well_note": "1-sentence drawdown and 1-minute pump cycle note"
    }},
    {{
      "badge": "Submersible Copper Cable",
      "title": "Twisted/Flat Jacketed Submersible Well Pump Copper Wire (3-Wire + Ground)",
      "price_range": "$139 - $469",
      "amazon_query": "12/3 10/3 Submersible Well Pump Copper Wire",
      "well_note": "1-sentence Franklin Electric AIM voltage drop note"
    }},
    {{
      "badge": "Brass Tank Tee & Switch",
      "title": "Lead-Free Brass Well Tank Tee Kit + Square D {psi_setting} Pressure Switch",
      "price_range": "$59 - $129",
      "amazon_query": "Brass Well Tank Tee Kit Square D 40/60 Pressure Switch",
      "well_note": "1-sentence relief valve and pressure switch note"
    }}
  ],
  "installation_checklist": [
    "Step 1 regarding tank pre-charge PSI (2 PSI below cut-in)",
    "Step 2 regarding brass check valves and torque arrestor placement",
    "Step 3 regarding waterproof heat-shrink submersible wire splices",
    "Step 4 regarding tank tee and pressure relief valve installation"
  ],
  "faqs": [
    {{"q": "How do I calculate Total Dynamic Head (TDH) for {item_name}?", "a": "Exact step-by-step TDH formula in feet."}},
    {{"q": "What size pressure tank do I need for {gpm} GPM?", "a": "Exact total tank gallons and usable drawdown gallons."}},
    {{"q": "What size submersible wire do I need for a {hp} HP pump at {depth_ft} feet?", "a": "Exact AWG copper wire specification."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{item_name}': {e}")

    return build_deterministic_well_data(well_tuple)


def build_well_html_page(data, slug, mon_cfg):
    well_name = data.get("well_name", "Submersible Well Pump System")
    sp = data.get("specs", {})
    depth_ft = int(safe_float(sp.get("pumping_depth_ft", 200), 200))
    tdh_ft = int(safe_float(sp.get("total_tdh_ft", 325), 325))
    gpm = int(safe_float(sp.get("flow_rate_gpm", 10), 10))
    hp = round(safe_float(sp.get("recommended_hp", 0.75), 0.75), 2)
    psi_str = sp.get("pressure_switch_psi", "40/60 PSI")
    precharge_psi = int(safe_float(sp.get("tank_precharge_psi", 38), 38))
    tank_gal = int(safe_float(sp.get("recommended_tank_gal", 44), 44))
    drawdown_gal = round(safe_float(sp.get("usable_drawdown_gal", 11.9), 11.9), 1)
    wire_awg = sp.get("recommended_wire_awg", "12 AWG Submersible Copper")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Submersible+Deep+Well+Pump+Pressure+Tank"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{well_name} TDH, Pressure Tank & Wire Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Submersible Well Pump")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-cyan-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Well Hardware')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$139+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">💧 {item.get('well_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Franklin Electric AIM 230V Wire & Tank Drawdown Reference Matrix
    matrix_rows_html = ""
    tiers = [
        ("100 ft Well (225 ft TDH)", "1/2 HP (10 GPM)", "32–44 Gal Tank (9.9 Gal DD)", "14 AWG / 12 AWG Copper", "15A 2-Pole (230V)"),
        ("175 ft Well (305 ft TDH)", "3/4 HP (10 GPM)", "44 Gal Tank (11.9 Gal DD)", "12 AWG Submersible", "15A 2-Pole (230V)"),
        ("250 ft Well (385 ft TDH)", "1.0 HP (10–12 GPM)", "44–62 Gal Tank (16.7 Gal DD)", "10 AWG Submersible", "20A 2-Pole (230V)"),
        ("350 ft Well (490 ft TDH)", "1.5 HP (10–15 GPM)", "62–86 Gal Tank (23.2 Gal DD)", "10 AWG / 8 AWG Copper", "20A 2-Pole (230V)"),
        ("450 ft Well (595 ft TDH)", "2.0 HP (10–12 GPM)", "86 Gal Tank (23.2 Gal DD)", "8 AWG Submersible", "25A 2-Pole (230V)")
    ]
    for d_s, p_s, t_s, w_s, b_s in tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{d_s}</td>
          <td class="py-3 px-4 font-bold text-cyan-400">{p_s}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{t_s}</td>
          <td class="py-3 px-4 text-slate-300">{w_s}</td>
          <td class="py-3 px-4 text-xs text-slate-400">{b_s}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("installation_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-cyan-500 rounded cursor-pointer well-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>NGWA Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', well_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', well_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-cyan-500 text-slate-950 px-2 py-0.5 rounded font-black">WELL</span>PumpIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Deep Well Pumps & Tanks →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-cyan-500 text-slate-950 px-3 py-1 rounded-full">{hp} HP | {gpm} GPM | {tdh_ft} ft TDH</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Tank: {tank_gal} Gal ({drawdown_gal} Gal Drawdown)</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{psi_str} (Pre-Charge: {precharge_psi} PSI) | {wire_awg}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', well_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-cyan-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>NGWA Hydraulic & Franklin AIM Summary:</strong> {data.get('hydraulic_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE TDH, PUMP HP, PRESSURE TANK & WIRE GAUGE CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {well_name} TDH, Tank & Wire Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your pumping water depth (feet), target household GPM flow rate, and pressure switch setting to compute exact Total Dynamic Head (TDH), required pump HP, tank gallon size, and 230V wire gauge.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="depthSlider" class="text-slate-300">Pumping Water Depth in Well (Feet)</label>
              <span class="text-cyan-400 font-bold"><span id="depthVal">{depth_ft}</span> ft</span>
            </div>
            <input id="depthSlider" type="range" min="40" max="550" step="10" value="{depth_ft}" class="w-full accent-cyan-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="gpmSlider" class="text-slate-300">Target Household Peak Flow Rate (GPM)</label>
              <span class="text-cyan-400 font-bold"><span id="gpmVal">{gpm}</span> GPM</span>
            </div>
            <input id="gpmSlider" type="range" min="5" max="25" step="1" value="{gpm}" class="w-full accent-cyan-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="switchSelect" class="block text-xs font-medium text-slate-400 mb-1">Pressure Switch Setting</label>
              <select id="switchSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="30/50" {"selected" if "30/50" in psi_str else ""}>30/50 PSI (Pre-charge 28 PSI)</option>
                <option value="40/60" {"selected" if "30/50" not in psi_str else ""}>40/60 PSI (Pre-charge 38 PSI)</option>
              </select>
            </div>
            <div>
              <label for="elevSelect" class="block text-xs font-medium text-slate-400 mb-1">Hill Elevation to House</label>
              <select id="elevSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="10" selected>Flat Lot (+10 ft)</option>
                <option value="35">Moderate Slope (+35 ft)</option>
                <option value="75">Hilltop Cabin (+75 ft)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-cyan-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-cyan-400 font-bold">Total Dynamic Head</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="tdhOut">{tdh_ft}</span> <span class="text-sm font-normal text-slate-400">ft TDH</span></div>
            <p id="pumpSpecOut" class="text-xs text-cyan-400 font-semibold mt-1">Need {hp} HP ({gpm} GPM) Pump</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Tank & 230V Wire</span>
            <div id="tankOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{tank_gal}-Gal Tank</div>
            <p id="wireOut" class="text-xs text-slate-300 font-semibold mt-1">Cable: {wire_awg}</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-cyan-950/40 border border-cyan-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="wellAdviceBanner" class="text-sm text-cyan-100 font-medium"></div>
        <a id="dynamicWellBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Well Pump & Tank on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {well_name} Pump, Tank & Cable Hardware Kit</h2>
        <span class="text-xs text-slate-400">NSF/ANSI-61 & Franklin AIM Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- WELL DEPTH, TDH & WIRE MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Deep Well Depth, TDH, Pump HP, Pressure Tank & Wire Chart (40/60 PSI)</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Well Depth (TDH)</th>
              <th class="py-3.5 px-4 text-cyan-400">Submersible Pump Spec</th>
              <th class="py-3.5 px-4 text-emerald-400">Pressure Tank (Drawdown)</th>
              <th class="py-3.5 px-4">230V Submersible Wire</th>
              <th class="py-3.5 px-4">Breaker Size</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- NGWA INSTALLATION CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">NGWA Submersible Pump & Pressure Tank Setup Checklist</h2>
        <span id="wellBadge" class="text-xs font-bold bg-slate-800 text-cyan-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({well_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} WellPumpIndex. Independent Ground Water Hydraulics & Submersible Pump Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const depthSlider = document.getElementById('depthSlider');
    const gpmSlider = document.getElementById('gpmSlider');
    const switchSelect = document.getElementById('switchSelect');
    const elevSelect = document.getElementById('elevSelect');
    const depthVal = document.getElementById('depthVal');
    const gpmVal = document.getElementById('gpmVal');
    const tdhOut = document.getElementById('tdhOut');
    const pumpSpecOut = document.getElementById('pumpSpecOut');
    const tankOut = document.getElementById('tankOut');
    const wireOut = document.getElementById('wireOut');
    const wellAdviceBanner = document.getElementById('wellAdviceBanner');
    const dynamicWellBtn = document.getElementById('dynamicWellBtn');

    function recalculateWell() {{
      const depth = parseInt(depthSlider.value, 10);
      const gpm = parseInt(gpmSlider.value, 10);
      const sw = switchSelect.value;
      const elev = parseInt(elevSelect.value, 10);

      depthVal.textContent = depth;
      gpmVal.textContent = gpm;

      const avgPsi = sw === '30/50' ? 40 : 50;
      const prechargePsi = sw === '30/50' ? 28 : 38;
      const ddFactor = sw === '30/50' ? 0.31 : 0.27;

      const pressureHeadFt = avgPsi * 2.31;
      const frictionFt = (depth + elev + 40) * 0.06;
      const totalTdh = Math.round(depth + elev + pressureHeadFt + frictionFt);

      let recHp = "1/2 HP";
      let hpNum = 0.5;
      if (totalTdh <= 230 && gpm <= 10) {{
        recHp = "1/2 HP";
        hpNum = 0.5;
      }} else if (totalTdh <= 320 && gpm <= 12) {{
        recHp = "3/4 HP";
        hpNum = 0.75;
      }} else if (totalTdh <= 410 && gpm <= 15) {{
        recHp = "1.0 HP";
        hpNum = 1.0;
      }} else if (totalTdh <= 520) {{
        recHp = "1.5 HP";
        hpNum = 1.5;
      }} else {{
        recHp = "2.0 HP";
        hpNum = 2.0;
      }}

      const minTotalTankGal = gpm / ddFactor;
      let stdTankGal = 20;
      if (minTotalTankGal <= 22) stdTankGal = 20;
      else if (minTotalTankGal <= 35) stdTankGal = 34;
      else if (minTotalTankGal <= 46) stdTankGal = 44;
      else if (minTotalTankGal <= 65) stdTankGal = 62;
      else stdTankGal = 86;

      const cableLen = depth + 50;
      let awgSpec = "12/3 AWG Copper";
      if (hpNum <= 0.75) awgSpec = cableLen <= 300 ? "12/3 AWG Submersible" : "10/3 AWG Submersible";
      else if (hpNum <= 1.0) awgSpec = cableLen <= 250 ? "12/3 AWG Submersible" : "10/3 AWG Submersible";
      else awgSpec = cableLen <= 280 ? "10/3 AWG Submersible" : "8/3 AWG Submersible";

      tdhOut.textContent = totalTdh;
      pumpSpecOut.textContent = `Match: ${{recHp}} (${{gpm}} GPM Series)`;
      tankOut.textContent = `${{stdTankGal}}-Gal Tank (Pre: ${{prechargePsi}} PSI)`;
      wireOut.textContent = `Cable: ${{awgSpec}}`;

      wellAdviceBanner.innerHTML = `💧 <strong>NGWA System Spec:</strong> For <strong>${{totalTdh}} ft TDH</strong>, install a <strong>${{recHp}} ${{gpm}} GPM 230V Stainless Submersible Pump</strong>, a <strong>${{stdTankGal}}-Gallon Diaphragm Tank</strong> (set to ${{prechargePsi}} PSI air charge), and <strong>${{awgSpec}} wire</strong>.`;
      dynamicWellBtn.href = `https://${{amzDomain}}/s?k=${{encodeURIComponent(recHp)}}+${{gpm}}+GPM+230V+Stainless+Submersible+Deep+Well+Pump+${{stdTankGal}}+Gallon+Pressure+Tank&tag=${{amzTag}}`;
    }}

    depthSlider.addEventListener('input', recalculateWell);
    gpmSlider.addEventListener('input', recalculateWell);
    switchSelect.addEventListener('change', recalculateWell);
    elevSelect.addEventListener('change', recalculateWell);
    recalculateWell();

    const checks = document.querySelectorAll('.well-check');
    const badge = document.getElementById('wellBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Submersible+Deep+Well+Pump+Pressure+Tank"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-cyan-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-cyan-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('hp', 0.75)} HP | {item.get('gpm', 10)} GPM</span>
            <span class="text-xs text-slate-400">{item.get('tdh_ft', 310)} ft TDH | {item.get('tank_gal', 44)}-Gal Tank</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-cyan-400 transition">{item['well_name']} Calculator</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-cyan-400">Calculate TDH, Tank & Wire Size →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WellPumpIndex — Deep Well Pump TDH, Pressure Tank & Wire Size Calculator (2026)</title>
  <meta name="description" content="Calculate exact submersible deep well pump Total Dynamic Head (TDH), diaphragm pressure tank drawdown gallons, and 230V copper wire gauge for Goulds, Grundfos, Franklin, Pentair, and Well-X-Trol systems.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="WellPumpIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-cyan-500 text-slate-950 px-2 py-0.5 rounded font-black">WELL</span>PumpIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Deep Well Pumps & Tanks →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Deep Well Pump TDH, Pressure Tank & Wire Sizing Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your well depth or submersible pump model below to calculate Total Dynamic Head (TDH), 40/60 PSI tank drawdown gallons, and Franklin AIM 230V wire gauge.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search well depth, pump or tank (e.g. 250 ft Well, Goulds 3/4 HP, Well-X-Trol WX-250, Grundfos, 44 Gallon...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-cyan-500">
      </div>
    </div>

    <div id="wellGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} WellPumpIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('wellGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>WellPumpIndex Deep Well Pump & Pressure Tank Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Submersible Well Pump TDH, Pressure Tank Drawdown & Wire Gauge Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_WELL:
        candidates.append((CUSTOM_WELL.strip(), 200, 10, 0.75, "40/60 PSI", 44))
    candidates.extend(SEED_WELLS)
    candidates.extend(discover_google_well_queries())

    new_urls = []
    count = 0

    for well_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        w_name = well_tuple[0]
        slug = slugify(f"{w_name}-tdh-tank-wire-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating well pump TDH & pressure tank calculator for: {w_name}...")
        try:
            data = generate_well_data(well_tuple)
            build_well_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "well_name": data.get("well_name", w_name),
                "slug": slug,
                "title": data.get("seo_title", f"{w_name} Well Pump Calculator"),
                "description": data.get("meta_description", ""),
                "hp": round(safe_float(sp.get("recommended_hp", well_tuple[3]), well_tuple[3]), 2),
                "gpm": int(safe_float(sp.get("flow_rate_gpm", well_tuple[2]), well_tuple[2])),
                "tdh_ft": int(safe_float(sp.get("total_tdh_ft", 310), 310)),
                "tank_gal": int(safe_float(sp.get("recommended_tank_gal", well_tuple[5]), well_tuple[5])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {w_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new well pump & pressure tank calculator pages.")


if __name__ == "__main__":
    main()
