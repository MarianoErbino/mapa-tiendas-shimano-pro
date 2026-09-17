# Mapa Tiendas Shimano PRO - Relanzamiento 2026

Mapa interactivo de las **344 tiendas** de la Base Shimano PRO ubicadas geograficamente por localidad, para responder por WhatsApp a quien pregunte por distribuidores cerca.

## Cómo abrirlo

`fetch()` no funciona con `file://`. Servir por HTTP:

```powershell
cd C:\Users\shimano.sandbox\Desktop\MAPA-TIENDAS-SHIMANO-PRO
python -m http.server 8000
# o
npx serve .
```

Y abrir http://localhost:8000

## Cómo se usa

- **Filtro de provincia** (dropdown, top-left): elegí la provincia que te preguntan y ves solo esas tiendas + zoom al área.
- **Buscador libre**: nombre, apellido, localidad, IG, mail, teléfono.
- **Clic en un item de la lista**: hace zoom + abre el popup del pin correspondiente.
- **Clic en el pin**: popup con contacto + 3 botones:
  - **WhatsApp** → abre wa.me con el número (asume prefijo AR, agrega `54` si falta).
  - **Ver IG** → abre el perfil de Instagram (si el handle no tiene espacios).
  - **Copiar contacto** → copia al portapapeles el bloque de texto listo para pegar en un chat.
- **Clic en una provincia (contorno)**: filtra y zoom automáticos.
- **Badge en el listado**:
  - `depto` (verde): el pin está en el centroide del **departamento** matcheado (183 tiendas).
  - `aprox` (amarillo): no se pudo matchear localidad → pin en el **centroide de la provincia** (158 tiendas).
  - `CABA` (azul): coordenada fija de CABA (3 tiendas).

## Archivos

- `index.html` — single-file, Leaflet 1.9.4 + markercluster vía CDN.
- `geo.json` — copia de MAPA-ARGENTINA (23 provincias + 527 departamentos).
- `stores.json` — 344 tiendas con lat/lng, generado por `build_stores.py`.
- `build_stores.py` — script que lee el Excel + normaliza + geocodifica por matcheo con geo.json.

## Actualizar los datos

Si Mariano recibe un Excel nuevo:

```powershell
cd C:\Users\shimano.sandbox\Desktop\MAPA-TIENDAS-SHIMANO-PRO
python build_stores.py
```

El script:
1. Lee `Desktop\Base limpia Shimano PRO - Relanzamiento 2026 FINAL.xlsx` (path fijo — cambialo en el script si movés el Excel).
2. Normaliza provincia (corrige typos: "Buenos aires"→"Buenos Aires", "cordoba"→"Cordoba", "Baradero"→"Buenos Aires", etc.).
3. Extrae la primera localidad de strings sucios (multilínea, con `,`, `/`, `y`, `-`, `(`).
4. Matchea localidad → departamento (fuzzy ratio ≥ 0.72) dentro de la provincia.
5. Calcula centroide del polígono matcheado (o de la provincia si no matcheó).
6. Sobrescribe `stores.json`.

Salida esperada: `Wrote 344 stores` + breakdown de match_quality.

## Limitaciones actuales

- 46% de los pins caen en el **centroide de la provincia** (badge `aprox`). Causas típicas:
  - Localidades que son **lugares de pesca**, no ciudades: "Río de la Plata", "Delta del Paraná", "Laguna San Lorenzo", "Bahía San Blas", "Mar Chiquita" (ambigua: hay depto BA + laguna SF).
  - Localidades **misspelled** más allá del threshold fuzzy (ej. "Remedios de escalda" → "Lomas de Zamora").
  - Ciudades chicas dentro de deptos con nombre distinto (ej. "El Tunal (rio juramento)" en Salta).
- Si querés mejorar precisión, corregí la columna `Localidad` en el Excel a nombre de **departamento** y volvé a correr `build_stores.py`.

## Datos sensibles

`stores.json` contiene teléfonos y mails. **No subir este mapa a un GitHub Pages público** sin autorización de las personas listadas.
