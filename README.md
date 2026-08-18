# Narvik Brief

En enkel daglig nyhetsbrief for Narvik og Nord-Norge.

## Struktur

- `index.html` – forsiden
- `styles.css` – design og responsiv layout
- `app.js` – laster og filtrerer nyhetene
- `data/news.json` – dagens publiserte saker
- `config/topics.json` – temaene briefen skal følge

## Daglig oppdatering

Nyhetsinnholdet i `data/news.json` er laget for å bli oppdatert hver morgen kl. 08:00 norsk tid. Den planlagte ChatGPT-jobben søker etter ferske saker, prioriterer dem etter temaene i `config/topics.json`, og kan deretter brukes til å oppdatere briefen.

## Publisering

Repoet kan publiseres som en statisk side med GitHub Pages. Aktiver Pages fra repository settings og velg `main` / root som kilde.
