"""Build stores.json from Base Shimano PRO Excel.

- Normaliza Provincia (trim + fix typos + title case)
- Extrae primera Localidad limpia (antes de coma/parentesis/salto/y//)
- Matchea localidad -> departamento del geo.json (fuzzy)
- Guarda lat/lng: centroide del depto si matchea, sino centroide de la provincia
- CABA = Buenos Aires provincia + coordenada fija de CABA
"""
from __future__ import annotations
import json, re, unicodedata
from pathlib import Path
import pandas as pd
from difflib import SequenceMatcher

ROOT = Path(r"C:/Users/shimano.sandbox/Desktop")
XLSX = ROOT / "Base limpia Shimano PRO - Relanzamiento 2026 FINAL.xlsx"
GEO  = ROOT / "MAPA-ARGENTINA/geo.json"
OUT  = ROOT / "MAPA-TIENDAS-SHIMANO-PRO/stores.json"

CABA_LATLNG = (-34.6037, -58.3816)

PROV_MAP = {
    "buenos aires": "Buenos Aires",
    "capital federal": "Ciudad Autonoma de Buenos Aires",
    "caba": "Ciudad Autonoma de Buenos Aires",
    "ciudad autonoma de buenos aires": "Ciudad Autonoma de Buenos Aires",
    "cordoba": "Cordoba",
    "corrientes": "Corrientes",
    "chaco": "Chaco",
    "chubut": "Chubut",
    "entre rios": "Entre Rios",
    "misiones": "Misiones",
    "neuquen": "Neuquen",
    "rio negro": "Rio Negro",
    "salta": "Salta",
    "san juan": "San Juan",
    "santa cruz": "Santa Cruz",
    "santa fe": "Santa Fe",
    "santiago del estero": "Santiago Del Estero",
    "tierra del fuego": "Tierra Del Fuego",
    "tucuman": "Tucuman",
    "baradero": "Buenos Aires",
    "canelones": "URUGUAY",
}

def strip_accents(s: str) -> str:
    if not isinstance(s, str): return ""
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(str(s or "")).lower().strip())

def norm_prov(p: str) -> str:
    key = norm(p)
    if key in PROV_MAP: return PROV_MAP[key]
    return " ".join(w.capitalize() for w in key.split())

def first_locality(txt: str) -> str:
    if not isinstance(txt, str): return ""
    t = txt.replace("\r", " ").replace("\n", " ").strip()
    for sep in [",", "/", "(", " y ", " - ", ".", ";", " zona "]:
        if sep in t.lower():
            t = t.split(sep, 1)[0] if sep != " y " else re.split(r"\s+y\s+", t, 1, flags=re.I)[0]
    return re.sub(r"\s+", " ", t).strip()

def polygon_centroid(coords):
    """Signed-area centroid of a polygon ring (lng, lat pairs)."""
    a = cx = cy = 0.0
    n = len(coords)
    for i in range(n):
        x0, y0 = coords[i]
        x1, y1 = coords[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-12:
        xs = [c[0] for c in coords]; ys = [c[1] for c in coords]
        return sum(xs)/len(xs), sum(ys)/len(ys)
    return cx / (6 * a), cy / (6 * a)

def ring_area(coords):
    a = 0.0
    n = len(coords)
    for i in range(n):
        x0, y0 = coords[i]
        x1, y1 = coords[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return abs(a) * 0.5

def feature_centroid(feat):
    """Return (lat, lng) centroid of the largest-area polygon of the feature.
    Prefers areas within Argentina bounds so islands like Antártida claim
    don't dominate Tierra del Fuego's centroid."""
    ARG_BOUNDS_LAT = (-56, -21)  # lat range
    geom = feat["geometry"]
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
        x, y = polygon_centroid(ring)
        return y, x  # lat, lng
    if geom["type"] == "MultiPolygon":
        # Sort polygons by area desc; pick the largest whose centroid is inside AR
        polys = sorted(geom["coordinates"], key=lambda p: ring_area(p[0]), reverse=True)
        for p in polys:
            x, y = polygon_centroid(p[0])
            if ARG_BOUNDS_LAT[0] <= y <= ARG_BOUNDS_LAT[1]:
                return y, x
        # Fallback: largest overall
        x, y = polygon_centroid(polys[0][0])
        return y, x
    return None

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# City/locality -> department name (as it appears in geo.json), by province_key
CITY_TO_DEPT = {
    "buenos aires": {
        "mar del plata": "General Pueyrredon",
        "miramar": "General Alvarado",
        "punta alta": "Coronel Rosales",
        "santa teresita": "La Costa",
        "mar de ajo": "La Costa",
        "mar de ajo norte": "La Costa",
        "san bernardo": "La Costa",
        "las toninas": "La Costa",
        "san clemente del tuyu": "La Costa",
        "villa gesell": "Villa Gesell",
        "carilo": "Pinamar",
        "pinamar": "Pinamar",
        "madariaga": "General Juan Madariaga",
        "general madariaga": "General Juan Madariaga",
        "gral madariaga": "General Juan Madariaga",
        "gral. madariaga": "General Juan Madariaga",
        "chascomus": "Chascomus",
        "san nicolas de los arroyos": "San Nicolas",
        "san nicolas": "San Nicolas",
        "ramallo": "Ramallo",
        "zarate": "Zarate",
        "berazategui": "Berazategui",
        "san fernando": "San Fernando",
        "tigre": "Tigre",
        "villa la nata": "San Fernando",
        "villa la nata": "San Fernando",
        "delta de san fernando": "San Fernando",
        "delta del parana": "San Fernando",
        "delta": "San Fernando",
        "remedios de escalada": "Lanus",
        "remedios de escalda": "Lanus",
        "quilmes": "Quilmes",
        "olavarria": "Olavarria",
        "cochico": "Adolfo Alsina",
        "alsina": "Adolfo Alsina",
        "guamini": "Guamini",
        "saladillo": "Saladillo",
        "bahia san blas": "Patagones",
        "coronel vidal": "Mar Chiquita",
        "balneario mar chiquita": "Mar Chiquita",
        "mar chiquita": "Mar Chiquita",
        "necochea": "Necochea",
        "tortuguitas": "Malvinas Argentinas",
        "san miguel": "San Miguel",
        "escobar": "Escobar",
        "pilar": "Pilar",
        "tres arroyos": "Tres Arroyos",
        "azul": "Azul",
        "tandil": "Tandil",
        "junin": "Junin",
        "pergamino": "Pergamino",
        "la plata": "La Plata",
        "berisso": "Berisso",
        "ensenada": "Ensenada",
        "pila": "Pila",
        "magdalena": "Magdalena",
        "trenque lauquen": "Trenque Lauquen",
        "bahia blanca": "Bahia Blanca",
    },
    "corrientes": {
        "goya": "Goya",
        "esquina": "Esquina",
        "paso de la patria": "San Cosme",
        "ita ibate": "General Paz",
        "ita-ibate": "General Paz",
        "empedrado": "Empedrado",
        "bella vista": "Bella Vista",
        "santo tome": "Santo Tome",
        "ituzaingo": "Ituzaingo",
        "corrientes": "Capital",
        "mercedes": "Mercedes",
        "curuzu cuatia": "Curuzu Cuatia",
        "monte caseros": "Monte Caseros",
        "paso de los libres": "Paso De Los Libres",
    },
    "entre rios": {
        "parana": "Parana",
        "concordia": "Concordia",
        "gualeguaychu": "Gualeguaychu",
        "gualeguay": "Gualeguay",
        "victoria": "Victoria",
        "villaguay": "Villaguay",
        "colon": "Colon",
        "diamante": "Diamante",
        "federal": "Federal",
        "concepcion del uruguay": "Uruguay",
        "villa paranacito": "Islas Del Ibicuy",
    },
    "santa fe": {
        "rosario": "Rosario",
        "santa fe": "La Capital",
        "reconquista": "General Obligado",
        "rafaela": "Castellanos",
        "venado tuerto": "General Lopez",
        "canada de gomez": "Iriondo",
        "san lorenzo": "San Lorenzo",
        "sunchales": "Castellanos",
        "esperanza": "Las Colonias",
    },
    "cordoba": {
        "cordoba": "Capital",
        "villa carlos paz": "Punilla",
        "rio cuarto": "Rio Cuarto",
        "villa maria": "General San Martin",
        "cosquin": "Punilla",
        "alta gracia": "Santa Maria",
        "jesus maria": "Colon",
        "san francisco": "San Justo",
    },
    "salta": {
        "salta": "Capital",
        "embarcacion": "General Jose de San Martin",
        "joaquin victor gonzalez": "Anta",
        "las lajitas": "Anta",
        "el tunal": "Anta",
        "tunal": "Anta",
    },
    "tierra del fuego": {
        "ushuaia": "Ushuaia",
        "rio grande": "Rio Grande",
    },
    "neuquen": {
        "neuquen": "Confluencia",
        "san martin de los andes": "Lacar",
        "villa la angostura": "Los Lagos",
        "junin de los andes": "Huiliches",
    },
    "rio negro": {
        "bariloche": "Bariloche",
        "san carlos de bariloche": "Bariloche",
        "viedma": "Adolfo Alsina",
        "cipolletti": "General Roca",
        "general roca": "General Roca",
    },
    "santiago del estero": {
        "santiago del estero": "Capital",
        "las termas": "Rio Hondo",
        "termas de rio hondo": "Rio Hondo",
    },
    "tucuman": {
        "san miguel de tucuman": "Capital",
        "tucuman": "Capital",
    },
    "chubut": {
        "comodoro rivadavia": "Escalante",
        "puerto madryn": "Biedma",
        "trelew": "Rawson",
        "esquel": "Futaleufu",
    },
    "santa cruz": {
        "rio gallegos": "Guer Aike",
        "el calafate": "Lago Argentino",
        "puerto deseado": "Deseado",
    },
    "misiones": {
        "posadas": "Capital",
        "obera": "Obera",
        "eldorado": "Eldorado",
        "puerto iguazu": "Iguazu",
    },
    "chaco": {
        "resistencia": "San Fernando",
        "saenz pena": "Comandante Fernandez",
    },
    "san juan": {
        "san juan": "Capital",
    },
}

def best_dept_match(loc_norm: str, prov_key: str, dept_index):
    """Return (dept_name, ratio) best match within province, or (None, 0)."""
    if prov_key not in dept_index or not loc_norm:
        return None, 0.0

    # 1) alias map for well-known cities/localities
    aliases = CITY_TO_DEPT.get(prov_key, {})
    if loc_norm in aliases:
        target = norm(aliases[loc_norm])
        for dname, dnorm_, _ in dept_index[prov_key]:
            if dnorm_ == target:
                return dname, 1.0
    # partial alias match (loc_norm contains an alias key)
    for alias_key, dept_target in aliases.items():
        if alias_key and alias_key in loc_norm:
            target = norm(dept_target)
            for dname, dnorm_, _ in dept_index[prov_key]:
                if dnorm_ == target:
                    return dname, 0.98

    # 2) fuzzy against actual dept names
    candidates = dept_index[prov_key]
    best_name, best_r = None, 0.0
    for dname, dnorm_, _ in candidates:
        if loc_norm == dnorm_:
            return dname, 1.0
        if dnorm_ in loc_norm or loc_norm in dnorm_:
            r = 0.92
        else:
            r = similar(loc_norm, dnorm_)
        if r > best_r:
            best_r, best_name = r, dname
    return best_name, best_r

def main():
    geo = json.loads(GEO.read_text(encoding="utf-8"))

    # Province centroids
    prov_cent = {}
    for feat in geo["prov"]["features"]:
        name = feat["properties"]["name"]
        prov_cent[norm(name)] = (feature_centroid(feat), name)

    # Dept index by province_norm
    dept_index: dict[str, list[tuple[str, str, tuple[float,float]]]] = {}
    for feat in geo["dept"]["features"]:
        pname = feat["properties"]["province"]
        dname = feat["properties"]["name"]
        cent = feature_centroid(feat)
        pkey = norm(pname)
        dept_index.setdefault(pkey, []).append((dname, norm(dname), cent))

    df = pd.read_excel(XLSX)
    df.columns = [c.strip() for c in df.columns]
    # rename accented col
    correo_col = next((c for c in df.columns if "correo" in c.lower()), None)
    porque_col = next((c for c in df.columns if "por qu" in c.lower()), None)

    stores = []
    stats = {"prov_ok": 0, "prov_fallback": 0, "dept_match": 0, "dept_miss": 0, "uruguay": 0}

    for _, row in df.iterrows():
        prov_raw = str(row.get("Provincia", "") or "").strip()
        loc_raw  = str(row.get("Localidad", "") or "").strip()
        prov_clean = norm_prov(prov_raw)

        if prov_clean == "URUGUAY":
            stats["uruguay"] += 1
            continue  # skip Uruguay rows (Canelones) - fuera de Argentina

        loc_first = first_locality(loc_raw)
        loc_norm  = norm(loc_first)

        # CABA special-case (no polygon in geo.json)
        if norm(prov_clean).startswith("ciudad autonoma") or loc_norm in ("caba", "ciudad autonoma de buenos aires"):
            lat, lng = CABA_LATLNG
            dept_name, ratio, quality = "CABA", 1.0, "caba"
            prov_display = "Ciudad Autonoma de Buenos Aires"
        else:
            pkey = norm(prov_clean)
            if pkey not in prov_cent:
                # last-chance: try the raw province
                pkey = norm(prov_raw)
            if pkey not in prov_cent:
                stats["prov_fallback"] += 1
                continue
            prov_cent_ll, prov_display = prov_cent[pkey]
            dept_name, ratio = best_dept_match(loc_norm, pkey, dept_index)
            if dept_name and ratio >= 0.72:
                # find centroid
                for dn, dnorm_, dcent in dept_index[pkey]:
                    if dn == dept_name:
                        lat, lng = dcent
                        break
                quality = "dept"
                stats["dept_match"] += 1
            else:
                lat, lng = prov_cent_ll
                dept_name, quality = None, "prov"
                stats["dept_miss"] += 1
            stats["prov_ok"] += 1

        stores.append({
            "nombre": str(row.get("Nombre", "") or "").strip(),
            "apellido": str(row.get("Apellido", "") or "").strip(),
            "telefono": str(row.get("Telefono", "") or "").strip(),
            "correo": str(row.get(correo_col, "") or "").strip() if correo_col else "",
            "instagram": str(row.get("Instagram", "") or "").strip(),
            "provincia_raw": prov_raw,
            "provincia": prov_display,
            "localidad_raw": loc_raw,
            "localidad": loc_first,
            "departamento": dept_name,
            "match_quality": quality,
            "match_ratio": round(ratio, 3) if 'ratio' in dir() else None,
            "lat": lat,
            "lng": lng,
        })

    OUT.write_text(json.dumps(stores, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(stores)} stores -> {OUT}")
    print("Stats:", json.dumps(stats, indent=2))

    # Distribution by province + match_quality
    prov_counts = {}
    for s in stores:
        prov_counts[s["provincia"]] = prov_counts.get(s["provincia"], 0) + 1
    print("\nBy province:")
    for p, c in sorted(prov_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {p}: {c}")

    qual = {}
    for s in stores:
        qual[s["match_quality"]] = qual.get(s["match_quality"], 0) + 1
    print("\nMatch quality:", qual)

if __name__ == "__main__":
    main()
