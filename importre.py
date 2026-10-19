# -*- coding: utf-8 -*-
# Requisito: pip install requests
import re
import difflib
import random
import shutil
import requests
from urllib.parse import unquote

# ==================== CONFIGURACIÓN ====================
WIKI_BASE = "https://digimon.fandom.com"       # datos: tipos, nivel, next forms
WIKI_ES   = "https://digimon.fandom.com/es"    # texto de la Pokedex (español)
ARCHIVO   = "pokemon.txt"
AUTO_EVOLUCIONES = True
STAT_MIN  = 20

HEADERS = {"User-Agent": "Mozilla/5.0 (rellenador personal)"}

PUNTOS_NIVEL = {
    "fresh": 200, "baby i": 200,
    "in-training": 300, "training": 300, "baby ii": 300,
    "rookie": 400, "child": 400,
    "champion": 500, "adult": 500,
    "ultimate": 600, "perfect": 600,
    "mega": 700, "final": 700,
}

EV_POR_NIVEL = {
    "fresh": (1, 1), "baby i": (1, 1),
    "in-training": (2, 2), "training": (2, 2), "baby ii": (2, 2),
    "rookie": (3, 2), "child": (3, 2),
    "champion": (4, 3), "adult": (4, 3),
    "ultimate": (5, 3), "perfect": (5, 3),
    "mega": (6, 4), "final": (6, 4),
}

NIVELES_EVO = {
    "baby i": 10, "baby ii": 14,
    "in-training": 14, "training": 14,
    "rookie": 22, "child": 22,
    "champion": 32, "adult": 32,
    "ultimate": 40, "perfect": 40,
    "mega": 58, "final": 58,
}
NIVEL_EVO_DEFECTO = 32

TIPOS_ES = {
    "slime": "Limo", "beast": "Bestia", "beastkin": "Bestia",
    "beast man": "Hombre bestia", "beastman": "Hombre bestia",
    "holy beast": "Bestia sagrada", "dark animal": "Animal oscuro",
    "mammal": "Mamífero", "animal": "Animal",
    "reptile": "Reptil", "dinosaur": "Dinosaurio", "dragon": "Dragón",
    "mythical dragon": "Dragón mítico", "exotic dragon": "Dragón exótico",
    "bird": "Ave", "bird man": "Hombre ave",
    "plant": "Planta", "vegetation": "Vegetación",
    "aquatic": "Acuático", "aqua": "Acuático", "sea animal": "Animal marino",
    "insect": "Insecto", "insectoid": "Insectoide",
    "machine": "Máquina", "cyborg": "Cíborg", "mineral": "Mineral",
    "holy": "Sagrado", "angel": "Ángel", "fallen angel": "Ángel caído",
    "fairy": "Hada", "demon": "Demonio", "demon man": "Demonio",
    "undead": "No-muerto", "skeleton": "Esqueleto", "ghost": "Fantasma",
    "wizard": "Mago", "mutant": "Mutante", "puppet": "Marioneta",
    "food": "Comida", "unique": "Único", "warrior": "Guerrero",
    "fire": "Fuego", "flame": "Fuego", "ice": "Hielo", "snow": "Nieve",
}

MAPEO_TIPOS = {
    "beast": "BEAST", "beastkin": "BEAST", "beast man": "BEAST",
    "beastman": "BEAST", "holy beast": "BEAST", "dark animal": "BEAST",
    "mammal": "BEAST", "animal": "BEAST",
    "reptile": "REPTILE", "dinosaur": "REPTILE", "dragon": "REPTILE",
    "mythical dragon": "REPTILE", "exotic dragon": "REPTILE",
    "bird": "BIRD", "bird man": "BIRD",
    "plant": "GRASS", "vegetation": "GRASS",
    "aquatic": "AQUATIC", "aqua": "AQUATIC", "sea animal": "AQUATIC",
    "insect": "BUG", "insectoid": "BUG",
    "machine": "MACHINE", "cyborg": "MACHINE", "mineral": "MACHINE",
    "holy": "SACRED", "angel": "SACRED", "fairy": "SACRED",
    "demon": "DEMON", "demon man": "DEMON", "fallen angel": "DEMON",
    "undead": "DEMON", "skeleton": "DEMON", "ghost": "DEMON",
    "evil": "DEMON", "wizard": "DEMON",
    "mutant": "QMARKS", "puppet": "QMARKS", "slime": "QMARKS",
    "food": "QMARKS", "unique": "QMARKS", "warrior": "QMARKS",
    "fire": "FIRE", "flame": "FIRE", "ice": "ICE", "snow": "ICE",
}

EXCEPCIONES_TIPO = {
    "Taomon": "SACRED",
}

HABILIDADES_POR_TIPO = {
    "BEAST":   ["Animal Instinct", "Ferocity", "Savage Fury"],
    "REPTILE": ["Reinforced Scales", "Predator", "Brutal Bite"],
    "BIRD":    ["Aerial Maneuver", "Sky Hunter", "Devastating Spike"],
    "BUG":     ["Exoskeleton", "Natural Toxin", "Swarm"],
    "AQUATIC": ["Water Acclimatization", "Natural Regeneration", "Marine Predator"],
    "GRASS":   ["Photosynthesis", "Spores", "Vines"],
    "DEMON":   ["Dark Curse", "Vital Drainage", "Bloodlust"],
    "SACRED":  ["Purification", "Sacred Light", "Divine Blessing"],
    "MACHINE": ["Metal Shielding", "Aiming System", "Emergency Protocol"],
    "FIRE":    ["Elemental Body", "Elemental Discharge", "Elemental Core"],
    "ICE":     ["Elemental Body", "Elemental Discharge", "Elemental Core"],
    "QMARKS":  [],
}

DEFAULTS = {
    "GenderRate": "Female50Percent", "GrowthRate": "Parabolic", "BaseEXP": "64",
    "Rareness": "45", "Happiness": "50",
    "HiddenAbility": "", "Moves": "", "Height": "0.7",
    "Weight": "6.9", "Color": "Yellow", "Habitat": "Grassland",
    "StepsToHatch": "5355", "Compatibility": "Field",
    "BattlerPlayerY": "24", "BattlerEnemyY": "32", "BattlerAltitude": "0",
}
COPIAR_ANTERIOR = ["BaseEXP", "Moves", "HiddenAbility",
                   "GenderRate", "GrowthRate", "Habitat", "StepsToHatch", "Compatibility"]

SECCIONES_PERFIL = ["profile", "perfil", "descripción", "descripcion",
                    "biografía", "biografia", "reference book"]

# ==================== LIMPIEZA DE WIKITEXTO ====================
NOMBRES_SIMPLES = {"nihongo", "tt", "ruby", "r", "sup", "sub", "tl", "transl"}

def reemplazar_plantillas(t, modo="texto"):
    """modo 'texto': nihongo/tt -> primer arg, resto se elimina.
       modo 'campo': nihongo/tt -> primer arg, resto -> args unidos con comas
       (así {{EvoList|[[Greymon]]|[[Tyrannomon]]}} se convierte en la lista)."""
    def sust(m):
        contenido = m.group(1)
        partes = contenido.split("|")
        if len(partes) < 2:
            return ""
        nombre = partes[0].strip().lower()
        args = partes[1:]
        if nombre in NOMBRES_SIMPLES:
            return args[0].strip()
        if modo == "texto":
            return ""
        validos = []
        for a in args:
            m2 = re.match(r"^\s*([^=]{1,25})=(.*)$", a, re.S)
            if m2:
                param = m2.group(1).strip().lower()
                if param in ("from", "prior", "pre", "prev", "image", "imagen"):
                    continue
                a = m2.group(2)
            if a.strip():
                validos.append(a.strip())
        return ",".join(validos)
    while "{{" in t:
        nuevo = re.sub(r"\{\{([^{}]*)\}\}", sust, t)
        if nuevo == t:
            break
        t = nuevo
    return t

def limpiar(t):
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = reemplazar_plantillas(t, "texto")
    t = re.sub(r"\[\[(?:File|Image|Archivo|Imagen|Category|Categoría)\s*:[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"__[A-Z]+__", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = t.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", t).strip()

def limpiar_campo(v):
    v = re.sub(r"<ref[^>]*/>", "", v)
    v = re.sub(r"<ref[^>]*>.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"<br\s*/?>", ", ", v, flags=re.I)
    v = re.sub(r"\n+", ", ", v)
    v = v.replace("*", " ")
    return limpiar_template_de_campo(v)

def limpiar_template_de_campo(v):
    v = reemplazar_plantillas(v, "campo")
    t = re.sub(r"\[\[(?:File|Image|Archivo|Imagen|Category|Categoría)\s*:[^\]]*\]\]", "", v, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = t.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", t).strip()

# ==================== PARSER DE INFOBOX ====================
def dividir_top(s):
    partes, buf, prof, i = [], "", 0, 0
    while i < len(s):
        dos = s[i:i+2]
        if dos in ("{{", "[["):
            prof += 1; buf += dos; i += 2
        elif dos in ("}}", "]]") and prof:
            prof -= 1; buf += dos; i += 2
        elif s[i] == "|" and prof == 0:
            partes.append(buf); buf = ""; i += 1
        else:
            buf += s[i]; i += 1
    partes.append(buf)
    return partes

def fin_de_plantilla(wt, ini):
    i, prof, n = ini, 0, len(wt)
    while i < n - 1:
        dos = wt[i:i+2]
        if dos == "{{":
            prof += 1; i += 2
        elif dos == "}}":
            prof -= 1; i += 2
            if prof == 0:
                return i
        else:
            i += 1
    return n

def todas_las_plantillas(wt):
    """Captura TODAS las plantillas, incluidas las anidadas dentro de otras."""
    res, i, n = [], 0, len(wt)
    while i < n - 1:
        if wt[i:i+2] == "{{":
            fin = fin_de_plantilla(wt, i)
            if fin > i + 2:
                res.append(wt[i:fin])
            i += 2          # sigue mirando DENTRO por si la infobox está anidada
        else:
            i += 1
    return res

PISTAS = ("type", "attribute", "level", "next", "prior", "family")

def parsear_infobox(wt, verbose=True):
    mejor, mejor_score, mejor_nombre = {}, -1, ""
    for plantilla in todas_las_plantillas(wt):
        partes = dividir_top(plantilla[2:-2])
        if len(partes) < 2:
            continue
        nombre = partes[0].strip().lower()
        info = {}
        for parte in partes[1:]:
            if "=" in parte:
                k, v = parte.split("=", 1)
                info[k.strip().lower()] = limpiar_campo(v)
        score = sum(1 for c in info if any(p in c for p in PISTAS))
        if "infobox" in nombre:
            score += 10
        if score > mejor_score:
            mejor, mejor_score, mejor_nombre = info, score, nombre
    if verbose:
        if mejor and any(p in c for c in mejor for p in PISTAS):
            print(f"↳ Infobox: '{mejor_nombre}' ({len(mejor)} campos)")
        elif mejor:
            print(f"⚠ Plantilla '{mejor_nombre}' sin campos útiles: {', '.join(sorted(mejor))[:200]}")
        else:
            print("⚠ No encontré infobox en la página.")
    return mejor

def buscar_campo(info, claves, evitar=("card", "tab", "gallery", "video")):
    for c in claves:
        if info.get(c):
            return info[c]
    for c in info:
        if any(e in c for e in evitar):
            continue
        for clave in claves:
            if clave in c and info[c]:
                return info[c]
    return ""

# ==================== EVOLUCIONES (3 estrategias) ====================
CLAVES_EVO_EXACTAS = ["next forms", "next form", "next", "evolves to",
                      "evolves into", "digivolves to", "digivolves into",
                      "next evolution", "to"]
CLAVES_EVO_PARCIALES = ["next form", "next", "evolves", "digivolves", "evolution"]
VALORES_VACIOS = ("none", "n/a", "—", "-", "unknown", "desconocido")

def campo_evoluciones(info):
    for c in CLAVES_EVO_EXACTAS:
        v = info.get(c, "").strip()
        if v and v.lower() not in VALORES_VACIOS:
            return v
    for c in info:
        if any(e in c for e in ("card", "tab", "gallery", "video", "image")):
            continue
        for clave in CLAVES_EVO_PARCIALES:
            if clave in c:
                v = info[c].strip()
                if v and v.lower() not in VALORES_VACIOS:
                    return v
    return ""

def secciones(wt):
    headers = list(re.finditer(r"^(={2,6})(.+?)\1\s*$", wt, re.M))
    secs = []
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(wt)
        secs.append((len(m.group(1)), m.group(2).strip().lower(), m.start(), end))
    return secs

def links_de(fragmento):
    res, vistos = [], set()
    lineas = fragmento.splitlines()
    for linea in lineas:
        if not re.match(r"\s*[\*\#:]", linea):
            continue
        m = re.search(r"\[\[([^\]|#]+)", linea)
        if not m:
            continue
        t = m.group(1).strip()
        if t and ":" not in t and not t.lower().startswith("list of") and t.lower() not in vistos:
            vistos.add(t.lower()); res.append(t)
    if not res:   # si no hay viñetas, coge todos los enlaces del bloque
        for m in re.finditer(r"\[\[([^\]|#]+)", fragmento):
            t = m.group(1).strip()
            if t and ":" not in t and not t.lower().startswith("list of") and t.lower() not in vistos:
                vistos.add(t.lower()); res.append(t)
    return res

def evoluciones_de_secciones(wt):
    subs_validas = ("to", "next", "next forms", "next form", "evolves to",
                    "digivolves to", "evolves into", "digivolves into")
    for i, (nivel, titulo, ini, fin) in enumerate(secciones(wt)):
        if "evolv" not in titulo and "digivolv" not in titulo:
            continue
        nombres, vistos = [], set()
        for j in range(i + 1, len(secs)):
            nl, nt, ni, nf = secs[j]
            if nl <= nivel:
                break
            if nt in subs_validas or nt.startswith(("evolves to", "digivolves to")):
                for link in links_de(wt[ni:nf]):
                    if link.lower() not in vistos:
                        vistos.add(link.lower()); nombres.append(link)
        if nombres:
            return nombres, titulo
    return [], ""

def internal(t):
    return re.sub(r"[^A-Za-z0-9]", "", t).upper()

def internal_evo(t):
    return internal(re.sub(r"\s*\([^)]*\)", "", t))

def internal_habilidad(nombre):
    return re.sub(r"[^A-Za-z0-9]", "", nombre).upper()

def evoluciones(wt, info):
    nombres = []
    # 1) Infobox
    crudos = campo_evoluciones(info)
    if crudos:
        nombres = [n.strip(" .,") for n in crudos.split(",")]
        nombres = [n for n in nombres if n]
        if nombres:
            print(f"↳ Evoluciones sacadas de la infobox ({len(nombres)}).")
    # 2) Sección 'Evolution' de la página
    if not nombres:
        nombres, fuente = evoluciones_de_secciones(wt)
        if nombres:
            print(f"↳ Evoluciones sacadas de la sección '{fuente}' ({len(nombres)}).")
    # 3) Manual
    if not nombres:
        print("⚠ No encontré 'Next forms' ni sección de evolución.")
        print(f"   Campos de la infobox: {', '.join(sorted(info)) if info else '(ninguna)'}")
        manual = input("   Escribe las evoluciones separadas por comas (Enter = vacío): ").strip()
        nombres = [n.strip() for n in manual.split(",")] if manual else []

    partes, vistos = [], set()
    for nombre in nombres:
        nombre = re.sub(r"\([^)]*\)", "", nombre).strip(" .,")
        if not nombre or nombre.lower() in vistos:
            continue
        vistos.add(nombre.lower())
        try:
            wt2, title = obtener_pagina(nombre)
            info2 = parsear_infobox(wt2, verbose=False)
            clave = detectar_nivel(buscar_campo(info2, ["level", "nivel"]))
            num = NIVELES_EVO.get(clave, NIVEL_EVO_DEFECTO)
        except Exception:
            title, num = nombre, NIVEL_EVO_DEFECTO
        partes += [internal_evo(title), "Level", str(num)]
        print(f"   ↳ Next form: {title} → Level {num}")
    return ",".join(partes)

# ==================== WIKI ====================
def nombre_desde_entrada(txt):
    m = re.search(r"/wiki/([^/?#]+)", txt.strip())
    if m:
        return unquote(m.group(1)).replace("_", " ")
    return txt.replace("_", " ").strip()

def obtener_pagina(nombre, base=WIKI_BASE):
    r = requests.get(f"{base}/api.php", params={
        "action": "parse", "page": nombre, "prop": "wikitext",
        "redirects": 1, "format": "json", "formatversion": "2",
    }, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data["error"]["info"])
    return data["parse"]["wikitext"], data["parse"]["title"]

def buscar_titulo(nombre, base):
    try:
        r = requests.get(f"{base}/api.php", params={
            "action": "query", "list": "search", "srsearch": nombre,
            "srlimit": 1, "format": "json", "formatversion": "2",
        }, headers=HEADERS, timeout=15)
        res = r.json().get("query", {}).get("search", [])
        return res[0]["title"] if res else ""
    except Exception:
        return ""

# ==================== POKEDEX (ESPAÑOL CON RESPALDO) ====================
def extraer_perfil(wt, title):
    m = re.search(r"\n==", wt)
    perfil = limpiar(wt[:m.start()] if m else wt)
    if len(perfil) < 80:
        for s in SECCIONES_PERFIL:
            m2 = re.search(rf"==+\s*{s}\s*==+\s*\n(.*?)(?=\n==|\Z)", wt, re.I | re.S)
            if m2:
                cand = limpiar(m2.group(1))
                if len(cand) > len(perfil):
                    perfil = cand
                break
    if not perfil:
        return ""
    return perfil if perfil.lower().startswith(title.lower()) else f"{title}, {perfil}"

def pokedex_es(title):
    try:
        wt_es, title_es = obtener_pagina(title, WIKI_ES)
    except Exception:
        alt = buscar_titulo(title, WIKI_ES)
        if not alt:
            return ""
        try:
            wt_es, title_es = obtener_pagina(alt, WIKI_ES)
        except Exception:
            return ""
    return extraer_perfil(wt_es, title_es)

# ==================== NIVEL, STATS Y EFFORT POINTS ====================
def detectar_nivel(texto):
    t = (texto or "").lower()
    for clave in sorted(PUNTOS_NIVEL, key=len, reverse=True):
        if clave in t:
            return clave
    return ""

def pedir_nivel_manual():
    print("⚠ No encontré el 'Level' en la wiki.")
    t = input("   Dime el nivel (fresh/in-training/rookie/champion/ultimate/mega): ").strip().lower()
    return t if t in PUNTOS_NIVEL else ""

def generar_stats(total):
    stats = [STAT_MIN] * 6
    for _ in range(total - STAT_MIN * 6):
        stats[random.randrange(6)] += 1
    return stats

def calcular_effort(stats, clave):
    if clave not in EV_POR_NIVEL:
        return "0,0,0,0,0,0"
    total, n_stats = EV_POR_NIVEL[clave]
    orden = sorted(range(6), key=lambda i: stats[i], reverse=True)
    ev = [0] * 6
    base, resto = divmod(total, n_stats)
    for rank, idx in enumerate(orden[:n_stats]):
        ev[idx] = base + (1 if rank < resto else 0)
    return ",".join(map(str, ev))

# ==================== TIPOS ====================
def primer_tipo(v):
    v = re.sub(r"\([^)]*\)", "", v or "")
    m = re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñü-]+", v)
    return m.group(0) if m else ""

def mapear_tipo(valor_casilla):
    v = (valor_casilla or "").replace("（", "(").replace("）", ")")
    v = re.sub(r"\([^)]*\)", "", v)
    v = re.sub(r"\s+", " ", v).strip().lower()
    for clave in sorted(MAPEO_TIPOS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(clave)}\b", v):
            return MAPEO_TIPOS[clave]
    for palabra in re.findall(r"[a-z]+", v):
        cercanas = difflib.get_close_matches(palabra, MAPEO_TIPOS.keys(), n=1, cutoff=0.75)
        if cercanas:
            return MAPEO_TIPOS[cercanas[0]]
    return "QMARKS"

# ==================== ARCHIVO ====================
def siguiente_num(texto):
    nums = [int(n) for n in re.findall(r"^\[(\d+)\]", texto, re.M)]
    return max(nums) + 1 if nums else 1

def entrada_anterior(texto):
    bloques = re.findall(r"^\[\d+\][^\n]*\n(.*?)(?=^\[\d+\]|\Z)", texto, re.M | re.S)
    if not bloques:
        return {}
    ant = {}
    for linea in bloques[-1].splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            ant[k.strip()] = v.strip()
    return ant

def construir_bloque(num, title, info, pokedex, evo, stats, effort, ant):
    attr_crudo = primer_tipo(buscar_campo(info, ["attribute", "atributo"])).lower()
    attribute = attr_crudo.upper() if attr_crudo in ("data", "vaccine", "virus") else "QMARKS"
    print(f"↳ Attribute wiki: '{attr_crudo}' → Type1={attribute}")

    tipo_crudo = buscar_campo(info, ["type", "tipo", "species", "especie"])
    type2 = EXCEPCIONES_TIPO.get(title) or mapear_tipo(tipo_crudo)
    tipo_limpio = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", tipo_crudo)).strip()
    clave = tipo_limpio.lower()
    kind = TIPOS_ES.get(clave)
    if not kind and clave:
        kind = TIPOS_ES.get(clave.split(" ")[0], clave.split(" ")[0].title())
    kind = kind or "?"
    print(f"↳ Type wiki: '{tipo_limpio}' → Type2={type2} / Kind={kind}")

    lista_habs = HABILIDADES_POR_TIPO.get(type2, [])
    habilidades = ",".join(internal_habilidad(h) for h in lista_habs)
    if habilidades:
        print(f"↳ Abilities ({type2}): {habilidades}")
    else:
        print(f"⚠ Type2={type2} sin habilidades automáticas, rellénalas a mano.")

    valores = {c: (ant.get(c) or d) if c in COPIAR_ANTERIOR else d
               for c, d in DEFAULTS.items()}
    datos = {
        "Name": title,
        "InternalName": internal(title),
        "Type1": attribute,
        "Type2": type2,
        "BaseStats": ",".join(map(str, stats)),
        "EffortPoints": effort,
        "Abilities": habilidades,
        "Kind": kind,
        "Pokedex": pokedex,
        "Evolutions": evo,
        "RegionalNumbers": f"{num},0",
        **valores,
    }
    orden = ["Name", "InternalName", "Type1", "Type2", "BaseStats", "GenderRate",
             "GrowthRate", "BaseEXP", "EffortPoints", "Rareness", "Happiness",
             "Abilities", "HiddenAbility", "Moves", "Height", "Weight", "Color",
             "Habitat", "StepsToHatch", "Kind", "Pokedex", "Compatibility",
             "RegionalNumbers", "BattlerPlayerY", "BattlerEnemyY", "BattlerAltitude",
             "Evolutions"]
    lineas = [f"[{num}]"] + [f"{c}={datos.get(c, '')}" for c in orden]
    return "\n".join(lineas)

def insertar(texto, bloque):
    t = texto.rstrip()
    if t.endswith("}"):
        return t[:-1].rstrip() + "\n" + bloque + "\n}\n"
    return t + "\n" + bloque + "\n"

# ==================== PROGRAMA ====================
def main():
    while True:
        entrada = input("\nNombre o URL del Digimon (Enter para salir): ").strip()
        if not entrada:
            break
        try:
            nombre = nombre_desde_entrada(entrada)
            wt, title = obtener_pagina(nombre)
        except Exception as e:
            print(f"✘ No se pudo leer de la wiki: {e}")
            continue

        info = parsear_infobox(wt)

        # NIVEL + STATS + EFFORT POINTS
        clave = detectar_nivel(buscar_campo(info, ["level", "nivel"]))
        if not clave:
            if info:
                print(f"⚠ No vi 'Level'. Campos: {', '.join(sorted(info))[:200]}")
            clave = pedir_nivel_manual()
        if clave:
            total = PUNTOS_NIVEL[clave]
            stats = generar_stats(total)
            effort = calcular_effort(stats, clave)
            print(f"↳ Nivel detectado: {clave} → BaseStats (total {total}): "
                  f"{','.join(map(str, stats))}")
            print(f"↳ EffortPoints (según sus mejores stats): {effort}")
        else:
            stats = [50] * 6
            effort = "0,0,0,0,0,0"
            print("⚠ Nivel desconocido: stats neutros y EV a 0, corrígelos a mano.")

        # EVOLUCIONES
        evo = evoluciones(wt, info) if AUTO_EVOLUCIONES else ""
        if AUTO_EVOLUCIONES and not evo:
            print("⚠ Evolutions queda vacío.")

        # POKEDEX: primero en español, respaldo en inglés
        pokedex = pokedex_es(title)
        if pokedex:
            print("↳ Pokedex: texto en español ✔")
        else:
            pokedex = extraer_perfil(wt, title)
            print("⚠ Pokedex: no hay texto en español, usando la wiki inglesa.")

        texto  = open(ARCHIVO, encoding="utf-8").read()
        num    = siguiente_num(texto)
        bloque = construir_bloque(num, title, info, pokedex, evo, stats, effort,
                                  entrada_anterior(texto))

        print("\n" + "-" * 60 + "\n" + bloque + "\n" + "-" * 60)
        if input("¿Añadir al archivo? (s/n): ").strip().lower().startswith("s"):
            shutil.copy(ARCHIVO, ARCHIVO + ".bak")
            with open(ARCHIVO, "w", encoding="utf-8") as f:
                f.write(insertar(texto, bloque))
            print(f"✔ {title} añadido como [{num}] (backup en {ARCHIVO}.bak)")

main()