# Abrahama 1A — strona z wizualizacjami

Interaktywna prezentacja biurowca: widok z lotu (dzień / zmierzch), wejście główne,
cztery piętra w przekroju i cztery lokale (2.01/2.09, 3.05, 4.12, 5.06/5.07).

Podgląd lokalny (przeglądarka potrzebuje serwera, który obsługuje zakresy bajtów dla wideo):

    py -3.11 serve.py

i otwórz http://localhost:8137 (porównanie obu wersji; same wersje są pod `/a/` i `/b/`).

Skąd biorą się pliki:

- `data.js` — `../build_site_data.py` (lokale, piętra, obrysy lokali z modelu Revit).
- `assets/video`, `assets/img` — `../build_site_media.py` pobiera klipy Higgsfield z
  `../hf_video_urls.json`, koduje je do H.264, odwraca każde przejście (klip powrotny)
  i zapętla pętle z ruchem.
- `app.js`, `styles.css`, `index.html` — strona; układ i mechanika z `revit-to-home-tour/run/sales-page-v2`.
