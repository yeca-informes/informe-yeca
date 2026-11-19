"""Genera datos_ejemplo.json e imagenes de prueba (datos inventados)."""
import json
import os
import random
from PIL import Image, ImageDraw, ImageFont

base = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(base, "ejemplo_img"), exist_ok=True)

posts_def = [
    ("CAROUSEL_ALBUM", "Lunes 9", "9T19:30", "Qué cambia con el nuevo esquema de subsidios al transporte: las 5 claves que tenés que saber antes de fin de mes", 31200, 1480, 212, 940, 610),
    ("REELS", "Lunes 9", "9T21:10", "Así quedó el Obelisco tras la tormenta de anoche. Mirá el video completo de lo que dejó el temporal en la Ciudad", 58400, 2210, 301, 520, 1480),
    ("IMAGE", "Martes 10", "10T08:05", "Buen día. Estas son las tapas de los diarios de hoy y los temas que marcan la agenda", 9800, 260, 18, 31, 22),
    ("CAROUSEL_ALBUM", "Miércoles 11", "11T12:40", "Inflación de octubre: el INDEC dio a conocer el dato y hay sorpresas en alimentos y servicios", 24100, 990, 143, 805, 377),
    ("VIDEO", "Jueves 12", "12T18:15", "Entrevista completa con la ministra de Educación sobre el calendario escolar 2027", 12700, 410, 66, 102, 95),
    ("IMAGE", "Viernes 13", "13T10:20", "Cierre de semana en los mercados: dólar, bonos y riesgo país en una sola imagen", 7600, 190, 9, 40, 15),
    ("REELS", "Sábado 14", "14T20:45", "El gol que paró el estadio: la jugada del sábado que todos comentan, en cámara lenta", 41900, 3050, 410, 700, 1920),
    ("CAROUSEL_ALBUM", "Domingo 15", "15T11:00", "Guía del finde largo: qué hacer, adónde ir y cuánto cuesta en 6 destinos cercanos", 18300, 870, 97, 1210, 530),
]
colores = ["#B0148F", "#2D3A8C", "#0F7B6C", "#C2410C", "#5B21B6", "#1D4ED8", "#9D174D", "#047857"]
try:
    fuente = ImageFont.truetype("arial.ttf", 90)
except OSError:
    fuente = ImageFont.load_default()

posts = []
for i, (tipo, dia, f, cap, alc, likes, com, gua, comp) in enumerate(posts_def, 1):
    nombre = f"post{i}.jpg"
    im = Image.new("RGB", (1080, 1350), colores[i - 1])
    dr = ImageDraw.Draw(im)
    dr.text((80, 560), f"Imagen de prueba {i}", fill="white", font=fuente)
    dr.text((80, 700), tipo, fill="white", font=fuente)
    im.save(os.path.join(base, "ejemplo_img", nombre), quality=90)
    inter = likes + com + gua + comp
    posts.append({
        "id": f"1790{i}", "fecha": f"2026-11-{int(f.split('T')[0]):02d}T{f.split('T')[1]}:00-03:00",
        "tipo": tipo, "caption": cap, "permalink": f"https://www.instagram.com/p/DRx{i}AbCdEf/",
        "imagen": f"ejemplo_img/{nombre}", "alcance": alc, "likes": likes, "comentarios": com,
        "guardados": gua, "compartidos": comp, "interacciones": inter,
        "engagement_pct": round(inter / alc * 100, 2),
    })

random.seed(7)
vals = []
for d in range(7):
    fila = []
    for h in range(24):
        base_v = 0.0
        if 7 <= h <= 23:
            base_v = random.uniform(0.5, 3.0)
        if h in (12, 13, 19, 20, 21):
            base_v += random.uniform(1.0, 3.0)
        if d >= 5 and h >= 18:
            base_v += 1.0
        fila.append(round(base_v, 2) if random.random() > 0.15 else 0)
    vals.append(fila)
vals[5][20] = 9.4

best = max(posts, key=lambda p: p["engagement_pct"])
worst = min(posts, key=lambda p: p["engagement_pct"])
tot_i = sum(p["interacciones"] for p in posts)
datos = {
    "cuenta": "dameyeca",
    "semana": {"desde": "2026-11-09", "hasta": "2026-11-15"},
    "resumen": {"seguidores": 48250, "seguidores_delta": 312, "alcance": 203800, "alcance_delta_pct": 12.4,
                "interacciones": tot_i, "engagement_pct": 5.62, "engagement_delta_pp": -0.4, "publicaciones": 8},
    "posts": posts,
    "mejor_post_id": best["id"], "peor_post_id": worst["id"],
    "heatmap": {"titulo": "Engagement promedio según día y hora de publicación (últimas 8 semanas)",
                "dias": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"], "horas": list(range(24)), "valores": vals},
    "por_formato": [
        {"tipo": "REELS", "posts": 2, "engagement_promedio": 7.4, "alcance_promedio": 50150},
        {"tipo": "CAROUSEL_ALBUM", "posts": 3, "engagement_promedio": 6.1, "alcance_promedio": 24533},
        {"tipo": "VIDEO", "posts": 1, "engagement_promedio": 5.4, "alcance_promedio": 12700},
        {"tipo": "IMAGE", "posts": 2, "engagement_promedio": 3.6, "alcance_promedio": 8700},
    ],
    "recomendaciones": {
        "resumen_editorial": "Semana fuerte para YECA: el alcance creció más de un 12 % y la cuenta sumó 312 seguidores nuevos. Los reels de actualidad urbana y deportes fueron los grandes motores, con el video del gol del sábado a la cabeza en interacciones. Los carruseles explicativos (subsidios, inflación y guía del finde) siguieron siendo los que más se guardan, señal de que la audiencia los toma como material de consulta. En cambio, las imágenes sueltas con tapas y cierres de mercado quedaron claramente por debajo: poco alcance y casi nada de conversación. El engagement general bajó 0,4 puntos porcentuales porque aumentó el alcance en gente que no nos sigue.",
        "contenido": [
            "Sumar al menos dos reels por semana con imágenes propias de la calle: son los que más alcance traen a gente nueva.",
            "Seguir con carruseles explicativos de 4 a 5 placas sobre economía y servicios; son los que más se guardan y se comparten por mensaje.",
            "Reemplazar las imágenes sueltas de tapas y cierres de mercado por un carrusel corto o un reel de 20 segundos.",
            "Cerrar cada carrusel con una pregunta a la audiencia para empujar los comentarios.",
        ],
        "horarios": [
            "Los sábados entre las 19 y las 21 h concentran el mejor engagement: reservar ese horario para el contenido más fuerte del finde.",
            "Entre semana, el pico está a las 12 h y a las 19 h; evitar publicar antes de las 8 h.",
            "Probar un reel el miércoles a las 20 h, un horario con poca competencia y buen rendimiento histórico.",
        ],
    },
}
with open(os.path.join(base, "datos_ejemplo.json"), "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=2)
print("ok")
