# Messier Best Moment

Programme Python pour calculer, pour chaque objet Messier (M1 a M110) et pour chaque jour d'une annee, l'instant de culmination (passage au meridien local), la direction de pointage, et la visibilite pendant la nuit astronomique.

## Fichiers du projet

- `messier_zenith.py` : script principal
- `messier_catalog.csv` : catalogue Messier (nom, nom familier, RA/Dec)

## Prerequis

- Python 3.10+ (teste avec Python 3.12)
- Aucun package externe requis (stdlib uniquement)

## Usage rapide

Depuis le dossier du projet :

```powershell
C:/Python312/python.exe .\messier_zenith.py --year 2026 --latitude "49 07 00 N" --longitude "2 18 00 E" --altitude-m 55
```

Ce mode genere un fichier :

- `messier_zenith_2026.csv`

## Mode resume

Le mode resume ne garde que les lignes ou l'objet est visible la nuit (entre coucher et lever astronomiques, Soleil a -18 deg).

```powershell
C:/Python312/python.exe .\messier_zenith.py --year 2026 --latitude "49 07 00 N" --longitude "2 18 00 E" --altitude-m 55 --resume
```

Ce mode genere par defaut :

- `messier_zenith_resume_2026.csv`

## Arguments

- `--year` (obligatoire) : annee a calculer, ex. `2026`
- `--latitude` (obligatoire) : latitude observateur
- `--longitude` (obligatoire) : longitude observateur
- `--altitude-m` (optionnel) : altitude observateur en metres (defaut: `0`)
- `--catalog` (optionnel) : chemin du catalogue (defaut: `messier_catalog.csv`, format `name;common_name;ra;dec`)
- `--output` (optionnel) : nom/chemin du CSV de sortie
- `--resume` (optionnel) : active le mode resume

## Formats acceptes pour latitude/longitude

1. Decimal

```text
--latitude 49.1167 --longitude 2.3000
```

2. DMS

```text
--latitude "49 07 00 N" --longitude "2 18 00 E"
```

Directions acceptees :

- Latitude : `N` ou `S`
- Longitude : `E` ou `O` (ou `W`)

## Colonnes du CSV

Separateur CSV : `;` (compatible Excel)

- `objet` : nom Messier (`M1` ... `M110`)
- `nom_familier` : nom usuel de l'objet quand disponible (ex: `Andromeda Galaxy` pour `M31`)
- `date` : date UTC (`YYYY-MM-DD`)
- `heure_utc` : heure UTC de culmination (`HH:MM:SS`)
- `altitude_deg` : altitude en degres
- `azimut_deg` : azimut en degres (0 = Nord, 90 = Est, 180 = Sud, 270 = Ouest)
- `direction` : direction globale (`N`, `NE`, `E`, `SE`, `S`, `SO`, `O`, `NO`)
- `visible_la_nuit` : `Oui` si la culmination est dans la nuit astronomique et au-dessus de l'horizon, sinon `Non`
- `lune_levee` : `Oui` si la Lune est au-dessus de l'horizon a l'instant de culmination, sinon `Non`
- `lune_age_jours` : age de la Lune en jours depuis la Nouvelle Lune (approximation)
- `lune_illumination_pct` : pourcentage illumine du disque lunaire (approximation)
- `distance_lune_objet_deg` : separation angulaire geocentrique entre la Lune et l'objet Messier (en degres)

## Exemple avec sortie personnalisee

```powershell
C:/Python312/python.exe .\messier_zenith.py --year 2027 --latitude "49 07 00 N" --longitude "2 18 00 E" --resume --output ".\resultats\messier_resume_2027.csv"
```

## Notes

- Mode complet : environ 110 lignes par jour (soit ~40150 lignes sur une annee non bissextile).
- Les heures sont en UTC.
- Le fichier est ecrit en `utf-8-sig` pour une meilleure ouverture dans Excel.
