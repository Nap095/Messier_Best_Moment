# Messier Best Moment

Programme Python pour calculer, pour chaque objet Messier (M1 a M110) et pour chaque jour d'une annee, l'instant de culmination (passage au meridien local), la direction de pointage, et la visibilite pendant la nuit astronomique.

## Installation

### 1. Recuperation depuis GitHub

Si le projet est deja publie sur GitHub, clonez-le avec :

```powershell
git clone https://github.com/Nap095/Messier_Best_Moment.git
cd Messier_Best_Moment
```

Si vous preferez telecharger une archive, ouvrez la page du depot GitHub puis utilisez le bouton de telechargement du code (format ZIP).

### 2. Configuration Python

Le programme ne depend que de la bibliotheque standard Python. Vous pouvez l'executer directement avec votre Python systeme ou dans un environnement virtuel.

Exemple avec un environnement virtuel local :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Execution

#### Mode interface (sans argument)

Si vous lancez le script sans argument, une interface Tkinter s'ouvre pour saisir les parametres.

```powershell
python .\messier_zenith.py
```

L'interface propose :

- une explication pour chaque champ (annee, latitude, longitude, etc.)
- un bouton pour lancer le calcul
- une langue par defaut en Francais avec possibilite de basculer en Anglais

#### Mode ligne de commande (avec arguments)

```powershell
python .\messier_zenith.py --year 2026 --latitude "49 07 00 N" --longitude "2 18 00 E" --altitude-m 55
```

Le fichier CSV est genere dans le dossier du projet. Par defaut, le nom est `messier_zenith_2026.csv`.

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

- `object` : nom Messier (`M1` ... `M110`)
- `common_name` : nom usuel de l'objet quand disponible (ex: `Andromeda Galaxy` pour `M31`)
- `date` : date UTC (`YYYY-MM-DD`)
- `utc_time` : heure UTC de culmination (`HH:MM:SS`)
- `altitude_deg` : altitude en degres
- `azimuth_deg` : azimut en degres (0 = Nord, 90 = Est, 180 = Sud, 270 = Ouest)
- `direction` : direction globale (`N`, `NE`, `E`, `SE`, `S`, `SO`, `O`, `NO`)
- `visible_at_night` : `Oui` si la culmination est dans la nuit astronomique et au-dessus de l'horizon, sinon `Non`
- `moon_up` : `Oui` si la Lune est au-dessus de l'horizon a l'instant de culmination, sinon `Non`
- `moon_age_days` : age de la Lune en jours depuis la Nouvelle Lune (approximation)
- `moon_illumination_pct` : pourcentage illumine du disque lunaire (approximation)
- `moon_object_distance_deg` : separation angulaire geocentrique entre la Lune et l'objet Messier (en degres)

## Exemple avec sortie personnalisee

```powershell
C:/Python312/python.exe .\messier_zenith.py --year 2027 --latitude "49 07 00 N" --longitude "2 18 00 E" --resume --output ".\resultats\messier_resume_2027.csv"
```

## Notes

- Mode complet : environ 110 lignes par jour (soit ~40150 lignes sur une annee non bissextile).
- Les heures sont en UTC.
- Le fichier est ecrit en `utf-8-sig` pour une meilleure ouverture dans Excel.
