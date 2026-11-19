"""Junta las métricas de Instagram de la semana y genera datos.json + miniaturas.

Uso: python obtener_datos.py carpeta_salida [AAAA-MM-DD]
  - La semana analizada va de domingo a sábado y termina el sábado anterior
    a la fecha dada (por defecto, hoy).
Credenciales: variables de entorno META_PAGE_TOKEN e IG_USER_ID,
o credenciales.txt en la carpeta del proyecto.
El campo "recomendaciones" queda vacío: lo completa el agente.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

API = "https://graph.facebook.com/v21.0"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
TIPOS = {"REELS": "REELS", "FEED": None, "STORY": "STORY"}


def cargar_credenciales():
    archivo = Path(__file__).resolve().parent.parent / "credenciales.txt"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    token, ig = os.environ.get("META_PAGE_TOKEN"), os.environ.get("IG_USER_ID")
    if not token or not ig:
        sys.exit("Faltan META_PAGE_TOKEN o IG_USER_ID")
    return token, ig


TOKEN, IG = cargar_credenciales()


def get(ruta, **params):
    params["access_token"] = TOKEN
    url = ruta if ruta.startswith("http") else f"{API}/{ruta}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode("utf-8", "replace")) from None


def tipo_post(m):
    if m.get("media_product_type") == "REELS":
        return "REELS"
    return m.get("media_type", "IMAGE")


def insights_post(mid):
    """Métricas de un posteo; si alguna no está disponible, sigue con las demás."""
    res = {}
    try:
        data = get(f"{mid}/insights", metric="reach,saved,shares,total_interactions,views")["data"]
    except RuntimeError:
        data = []
        for met in ("reach", "saved", "shares", "total_interactions", "views"):
            try:
                data += get(f"{mid}/insights", metric=met)["data"]
            except RuntimeError:
                pass
    for d in data:
        res[d["name"]] = d["values"][0]["value"]
    return res


def traer_posts(desde):
    campos = ("id,caption,timestamp,media_type,media_product_type,permalink,"
              "media_url,thumbnail_url,like_count,comments_count")
    resp = get(f"{IG}/media", fields=campos, limit=50)
    posts = []
    while True:
        for m in resp.get("data", []):
            fecha = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TZ)
            if fecha < desde:
                return posts
            m["_fecha"] = fecha
            posts.append(m)
        siguiente = resp.get("paging", {}).get("next")
        if not siguiente:
            return posts
        resp = get(siguiente)


def armar_post(m):
    ins = insights_post(m["id"])
    likes, com = m.get("like_count", 0) or 0, m.get("comments_count", 0) or 0
    guard, comp = ins.get("saved", 0), ins.get("shares", 0)
    inter = ins.get("total_interactions") or (likes + com + guard + comp)
    alcance = ins.get("reach", 0)
    return {
        "id": m["id"],
        "fecha": m["_fecha"].isoformat(),
        "tipo": tipo_post(m),
        "caption": (m.get("caption") or "").strip(),
        "permalink": m.get("permalink", ""),
        "imagen": None,
        "_img_url": m.get("thumbnail_url") or m.get("media_url"),
        "alcance": alcance,
        "vistas": ins.get("views", 0),
        "likes": likes,
        "comentarios": com,
        "guardados": guard,
        "compartidos": comp,
        "interacciones": inter,
        "engagement_pct": round(inter / alcance * 100, 2) if alcance else 0.0,
    }


def bajar_imagen(post, carpeta):
    url = post.pop("_img_url", None)
    if not url:
        return
    destino = carpeta / f"{post['id']}.jpg"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            destino.write_bytes(r.read())
        post["imagen"] = f"img/{destino.name}"
    except Exception:
        pass


def totales(posts):
    alc = sum(p["alcance"] for p in posts)
    inter = sum(p["interacciones"] for p in posts)
    return alc, inter, (inter / alc * 100 if alc else 0.0)


def nuevos_seguidores(desde, hasta):
    try:
        d = get(f"{IG}/insights", metric="follower_count", period="day",
                since=int(desde.timestamp()), until=int(hasta.timestamp()))["data"]
        return sum(v["value"] for v in d[0]["values"])
    except (RuntimeError, IndexError, KeyError):
        return None


def main():
    salida = Path(sys.argv[1])
    hoy = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(TZ).date()
    # Último sábado completo antes de "hoy"
    sabado = hoy - timedelta(days=(hoy.weekday() - 5) % 7 or 7)
    domingo = sabado - timedelta(days=6)
    ini = datetime.combine(domingo, time(0), TZ)
    fin = datetime.combine(sabado + timedelta(days=1), time(0), TZ)
    ini_ant = ini - timedelta(days=7)
    ini_4sem = fin - timedelta(days=28)

    img_dir = salida / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    crudos = [m for m in traer_posts(ini_4sem) if m["_fecha"] < fin
              and m.get("media_product_type") != "STORY"]
    print(f"Posteos últimas 4 semanas: {len(crudos)}", file=sys.stderr)
    todos = [armar_post(m) for m in crudos]
    for p, m in zip(todos, crudos):
        p["_dt"] = m["_fecha"]

    semana = [p for p in todos if ini <= p["_dt"] < fin]
    anterior = [p for p in todos if ini_ant <= p["_dt"] < ini]
    for p in semana:
        bajar_imagen(p, img_dir)

    # Heatmap: alcance típico (mediana, para que un viral aislado no lo deforme)
    # según día y hora de publicación, últimas 4 semanas
    acum = defaultdict(list)
    for p in todos:
        acum[(p["_dt"].weekday(), p["_dt"].hour)].append(p["alcance"])
    valores = [[round(median(acum[(d, h)])) if acum[(d, h)] else 0
                for h in range(24)] for d in range(7)]

    por_tipo = defaultdict(list)
    for p in todos:
        por_tipo[p["tipo"]].append(p)
    nombres = {"REELS": "Reels", "CAROUSEL_ALBUM": "Carrusel", "IMAGE": "Foto", "VIDEO": "Video"}
    por_formato = [{
        "tipo": nombres.get(t, t),
        "posts": len(ps),
        "engagement_promedio": round(sum(x["engagement_pct"] for x in ps) / len(ps), 2),
        "alcance_promedio": round(sum(x["alcance"] for x in ps) / len(ps)),
    } for t, ps in sorted(por_tipo.items(), key=lambda kv: -len(kv[1]))]

    alc, inter, eng = totales(semana)
    alc_a, _, eng_a = totales(anterior)
    perfil = get(IG, fields="followers_count,username")
    con_alcance = [p for p in semana if p["alcance"]] or semana
    ordenados = sorted(con_alcance, key=lambda p: p["engagement_pct"])
    # El "mejor" se elige entre los posteos con alcance igual o mayor a la mediana,
    # para que no gane uno que casi nadie vio.
    alcances = sorted(p["alcance"] for p in con_alcance)
    mediana = alcances[len(alcances) // 2] if alcances else 0
    candidatos_mejor = [p for p in ordenados if p["alcance"] >= mediana] or ordenados

    for p in todos:
        p.pop("_dt", None)
        p.pop("_img_url", None)

    datos = {
        "cuenta": perfil.get("username", "dameyeca"),
        "semana": {"desde": domingo.isoformat(), "hasta": sabado.isoformat()},
        "resumen": {
            "seguidores": perfil.get("followers_count", 0),
            "seguidores_delta": nuevos_seguidores(ini, fin),
            "alcance": alc,
            "alcance_delta_pct": round((alc - alc_a) / alc_a * 100, 1) if alc_a else None,
            "interacciones": inter,
            "engagement_pct": round(eng, 2),
            "engagement_delta_pp": round(eng - eng_a, 2) if anterior else None,
            "publicaciones": len(semana),
        },
        "posts": sorted(semana, key=lambda p: p["fecha"]),
        "mejor_post_id": candidatos_mejor[-1]["id"] if candidatos_mejor else "",
        "peor_post_id": ordenados[0]["id"] if ordenados else "",
        "heatmap": {"titulo": "Alcance típico según día y hora de publicación (últimas 4 semanas)",
                    "dias": DIAS, "horas": list(range(24)), "valores": valores},
        "por_formato": por_formato,
        "recomendaciones": {"resumen_editorial": "", "contenido": [], "horarios": []},
        "_contexto": {
            "nota": "Datos extra para que el agente escriba las recomendaciones; el PDF no los usa.",
            "semana_anterior": {"publicaciones": len(anterior), "alcance": alc_a,
                                "engagement_pct": round(eng_a, 2)},
            "posts_4_semanas": [{k: p[k] for k in ("fecha", "tipo", "alcance", "vistas",
                                 "interacciones", "engagement_pct", "guardados", "compartidos")}
                                | {"caption": p["caption"][:100]} for p in todos],
        },
    }
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(semana)} posteos de la semana {domingo} a {sabado} -> {salida / 'datos.json'}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
