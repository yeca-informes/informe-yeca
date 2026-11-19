# Informe semanal de Instagram — YECA

Genera cada domingo un PDF con las métricas de la semana de @dameyeca y lo manda por mail.

1. `python obtener_datos.py salida`: genera `salida/datos.json` y las miniaturas.
2. Se completan las `recomendaciones` en `datos.json`.
3. `python armar_pdf.py salida/datos.json salida/Informe_YECA.pdf`
4. `python enviar.py salida/Informe_YECA.pdf "Asunto" mail1 mail2 ...`

Credenciales por variables de entorno: `META_PAGE_TOKEN`, `IG_USER_ID`, `GMAIL_USUARIO`, `GMAIL_APP_PASSWORD`. Nunca se suben al repositorio.
