# SpreukDB — RFB Consult

Flask + SQLite applicatie voor het beheren van een persoonlijke spreukencollectie. Met wachtwoord bescherming.

## Installatie

```bash
cd spreuken_app
pip install flask
python app.py
```

Open dan: http://localhost:5001

## iPad-toegang

Start op de Mac, zoek het lokale IP-adres:
```bash
ipconfig getifaddr en0
```
Open op de iPad: http://192.168.x.x:5001

## Database-velden per spreuk

| Veld | Beschrijving |
|------|-------------|
| tekst_nl | Nederlandse tekst (verplicht) |
| tekst_en | Engelse vertaling |
| auteur | Naam van de auteur / spreker |
| bron | Boek, toespraak of andere bron |
| origine | Land, periode, culturele context |
| taal_origineel | nl / en / de / fr / la / anders |
| categorie_id | Koppeling naar categorie |
| datum_toegevoegd | Datum van invoer |
| notitie | Persoonlijk commentaar |
| favoriet | 0 / 1 vlag |

## Functies

- Zoeken op tekst, auteur
- Filteren op categorie, taal, favoriet
- Spreuk van de dag (willekeurig)
- Tags (vrije trefwoorden)
- Export naar CSV en JSON
- Categorieënbeheer
- iPad-vriendelijke interface

## Bestandsstructuur

```
spreuken_app/
  app.py              — Flask applicatie + routes
  spreuken.db         — SQLite database (aangemaakt bij eerste start)
  requirements.txt
  templates/
    base.html         — Navigatie, stijlen
    index.html        — Overzicht + zoekfilters
    form.html         — Invoer- en bewerkformulier
    categorieen.html  — Categoriebeheer
```
