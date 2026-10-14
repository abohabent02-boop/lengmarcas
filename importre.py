# -*- coding: utf-8 -*-
# Requisito: pip install requests
import re
import difflib
import random
import shutil
import requests
from urllib.parse import unquote

# ==================== CONFIGURACIÓN ====================
WIKI_BASE = "https://digimon.fandom.com"   # wiki de las capturas (inglés)
ARCHIVO   = "pokemon.txt"
AUTO_EVOLUCIONES = True                    # False = dejar Evolutions vacío
STAT_MIN  = 20                             # valor mínimo de cada stat al repartir

HEADERS = {"User-Agent": "Mozilla/5.0 (rellenador personal)"}

# Nivel de la wiki -> puntos totales a repartir en BaseStats
PUNTOS_NIVEL = {
    "fresh": 200, "baby i": 200,
    "in-training": 300, "training": 300, "baby ii": 300,
    "rookie": 400, "child": 400,
    "champion": 500, "adult": 500,
    "ultimate": 600, "perfect": 600,
    "mega": 700, "final": 700,
}

# Nivel del Digimon DESTINO -> número de Level en Evolutions
NIVELES_EVO = {
    "baby i": 10, "baby ii": 14,
    "in-training": 14, "training": 14,
    "rookie": 22, "child": 22,
    "champion": 32, "adult": 32,
    "ultimate": 40, "perfect": 40,
    "mega": 58, "final": 58,
}
NIVEL_EVO_DEFECTO = 32

# Traducción al español del tipo original (solo informativo, va en Kind)
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

# Tipo de la wiki -> InternalName de TU types.txt
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

# Excepciones puntuales por Digimon (nombre exacto de la wiki -> tu tipo)
EXCEPCIONES_TIPO = {
    "Taomon": "SACRED",
}

# Habilidades automáticas según el Type2
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
    "EffortPoints": "0,0,0,0,0,0", "Rareness": "45", "Happiness": "50",
    "HiddenAbility": "", "Moves": "", "Height": "0.7",
    "Weight": "6.9", "Color": "Yellow", "Habitat": "Grassland",
    "StepsToHatch": "5355", "Compatibility": "Field",
    "BattlerPlayerY": "24", "BattlerEnemyY": "32", "BattlerAltitude": "0",
}
COPIAR_ANTERIOR = ["BaseEXP", "EffortPoints", "Moves", "HiddenAbility",
                   "GenderRate", "GrowthRate", "Habitat", "StepsToHatch", "Compatibility"]

# ==================== LIMPIEZA DE WIKITEXTO ====================
def reemplazar_plantillas(t, conservar=True):
    """{{plantilla|a|b}} -> 'a' (o '' si conservar=False). nihongo|Beast|獣 -> Beast"""
    def sust(m):
        contenido = m.group(1)
        if conservar and "|" in contenido:
            primero = contenido.split("|")[1].strip()
            if primero:
                return primero
        return ""
    while "{{" in t:
        nuevo = re.sub(r"\{\{([^{}]*)\}\}", sust, t)
        if nuevo == t:
            break
        t = nuevo
    return t

def limpiar(t, conservar=False):
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = reemplazar_plantillas(t, conservar)
    t = re.sub(r"\[\[(?:File|Image|Archivo|Imagen|Category|Categoría)\s*:[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"__[A-Z]+__", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = t.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", t).strip()

def limpiar_campo(v):
    """Para casillas de infobox: <br> y saltos de línea se convierten en comas."""
    v = re.sub(r"<ref[^>]*/>", "", v)
    v = re.sub(r"<ref[^>]*>.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"<br\s*/?>", ", ", v, flags=re.I)
    v = re.sub(r"\n+", ", ", v)
    v = v.replace("*", " ")
    return limpiar(v, conservar=True)

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

def plantillas_top(wt):
    """Devuelve TODAS las plantillas de primer nivel de la página."""
    res, i, n = [], 0, len(wt)
    while i < n - 1:
        if wt[i:i+2] == "{{":
            fin = fin_de_plantilla(wt, i)
            res.append(wt[i:fin])
            i = fin
        else:
            i += 1
    return res

PISTAS = ("type", "attribute", "level", "next")

def parsear_infobox(wt, verbose=True):
    """Busca entre TODAS las plantillas la que sea la infobox del Digimon."""
    mejor, mejor_score, mejor_nombre = {}, -1, ""
    for plantilla in plantillas_top(wt):
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
        if "infobox" in nombre or "digimon" in nombre:
            score += 10
        if score > mejor_score:
            mejor, mejor_score, mejor_nombre = info, score, nombre
    if verbose:
        if mejor and any(PISTA in c for c in mejor for PISTA in PISTAS):
            print(f"↳ Infobox encontrada: '{mejor_nombre}' ({len(mejor)} campos)")
        elif mejor:
            print(f"⚠ Plantilla '{mejor_nombre}' encontrada pero sin campos útiles.")
        else:
            print("⚠ No encontré ninguna infobox en la página.")
    return mejor

def buscar_campo(info, claves, evitar=("card",)):
    """Primero nombre exacto, luego parcial ('Type', 'tipo', 'next forms'...)."""
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

# ==================== TIPOS ====================
def primer_tipo(v):
    v = re.sub(r"\([^)]*\)", "", v or "")
    m = re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñü-]+", v)
    return m.group(0) if m else ""

def mapear_tipo(valor_casilla):
    """Casilla 'Type' de la wiki -> uno de tus tipos. Si nada encaja, QMARKS."""
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

def internal(t):
    return re.sub(r"[^A-Za-z0-9]", "", t).upper()

def internal_habilidad(nombre):
    return re.sub(r"[^A-Za-z0-9]", "", nombre).upper()

# ==================== WIKI ====================
def nombre_desde_entrada(txt):
    m = re.search(r"/wiki/([^/?#]+)", txt.strip())
    if m:
        return unquote(m.group(1)).replace("_", " ")
    return txt.replace("_", " ").strip()

def obtener_pagina(nombre):
    r = requests.get(f"{WIKI_BASE}/api.php", params={
        "action": "parse", "page": nombre, "prop": "wikitext",
        "redirects": 1, "format": "json", "formatversion": "2",
    }, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data["error"]["info"])
    return data["parse"]["wikitext"], data["parse"]["title"]

# ==================== NIVEL Y STATS ====================
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
    return ",".join(map(str, stats))

# ==================== POKEDEX Y EVOLUCIONES ====================
def texto_pokedex(wt, title):
    m = re.search(r"\n==", wt)
    perfil = limpiar(wt[:m.start()] if m else wt)
    if len(perfil) < 80:
        m2 = re.search(r"==+\s*(?:profile|perfil)\s*==+\s*\n(.*?)(?=\n==|\Z)", wt, re.I | re.S)
        if m2:
            perfil = limpiar(m2.group(1))
    if not perfil:
        return ""
    return perfil if perfil.lower().startswith(title.lower()) else f"{title}, {perfil}"

def evoluciones(info):
    crudos = buscar_campo(info, ["next forms", "next form", "next",
                                 "evolves to", "evolves into"])
    if not crudos:
        return ""
    partes = []
    for nombre in [n.strip(" .,") for n in crudos.split(",") if n.strip(" .,")]:
        nombre = re.sub(r"\([^)]*\)", "", nombre).strip()
        if not nombre:
            continue
        try:
            wt2, title = obtener_pagina(nombre)
            info2 = parsear_infobox(wt2, verbose=False)
            clave = detectar_nivel(buscar_campo(info2, ["level", "nivel"]))
            num = NIVELES_EVO.get(clave, NIVEL_EVO_DEFECTO)
        except Exception:
            title, num = nombre, NIVEL_EVO_DEFECTO
        partes += [internal(title), "Level", str(num)]
        print(f"   ↳ Next form: {title} → Level {num}")
    return ",".join(partes)

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

def construir_bloque(num, title, info, pokedex, evo, stats, ant):
    # Type1 = Attribute de la wiki (Data/Virus/Vaccine; resto -> QMARKS)
    attr_crudo = primer_tipo(buscar_campo(info, ["attribute", "atributo"])).lower()
    attribute = attr_crudo.upper() if attr_crudo in ("data", "vaccine", "virus") else "QMARKS"
    print(f"↳ Attribute wiki: '{attr_crudo}' → Type1={attribute}")

    # Type2 = mapeado a TUS tipos; Kind = tipo original traducido (informativo)
    tipo_crudo = buscar_campo(info, ["type", "tipo", "species", "especie"])
    if not tipo_crudo:
        print(f"⚠ Casilla 'Type' no encontrada. Campos de la infobox: {', '.join(sorted(info))[:200]}")
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
        "BaseStats": stats,
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

        # NIVEL + STATS ALEATORIOS
        clave = detectar_nivel(buscar_campo(info, ["level", "nivel"]))
        if not clave:
            if info:
                print(f"⚠ No vi 'Level'. Campos: {', '.join(sorted(info))[:200]}")
            clave = pedir_nivel_manual()
        if clave:
            total = PUNTOS_NIVEL[clave]
            stats = generar_stats(total)
            print(f"↳ Nivel detectado: {clave} → BaseStats aleatorios (total {total}): {stats}")
        else:
            stats = "50,50,50,50,50,50"
            print("⚠ Nivel desconocido: pongo stats neutros, corrígelos a mano.")

        # EVOLUCIONES
        evo = evoluciones(info) if AUTO_EVOLUCIONES else ""
        if AUTO_EVOLUCIONES and not evo:
            print("⚠ Sin 'Next forms' en la wiki: Evolutions queda vacío.")

        texto  = open(ARCHIVO, encoding="utf-8").read()
        num    = siguiente_num(texto)
        bloque = construir_bloque(num, title, info, texto_pokedex(wt, title),
                                  evo, stats, entrada_anterior(texto))

        print("\n" + "-" * 60 + "\n" + bloque + "\n" + "-" * 60)
        if input("¿Añadir al archivo? (s/n): ").strip().lower().startswith("s"):
            shutil.copy(ARCHIVO, ARCHIVO + ".bak")
            with open(ARCHIVO, "w", encoding="utf-8") as f:
                f.write(insertar(texto, bloque))
            print(f"✔ {title} añadido como [{num}] (backup en {ARCHIVO}.bak)")

main()