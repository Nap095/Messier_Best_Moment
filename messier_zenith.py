from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


UTC = timezone.utc
TARGET_SUN_ALT = -18.0
SYNODIC_MONTH_DAYS = 29.530588853


@dataclass(frozen=True)
class MessierObject:
	name: str
	common_name: str
	ra_hours: float
	dec_deg: float


def normalize_hours(value: float) -> float:
	return value % 24.0


def normalize_degrees(value: float) -> float:
	return value % 360.0


def parse_angle(text: str, is_latitude: bool) -> float:
	cleaned = text.strip().upper().replace(",", ".")
	if re.fullmatch(r"[-+]?\d+(\.\d+)?", cleaned):
		return float(cleaned)

	sign = 1.0
	if any(letter in cleaned for letter in ["S", "O", "W"]):
		sign = -1.0
	if any(letter in cleaned for letter in ["N", "E"]):
		sign = 1.0
	if cleaned.startswith("-"):
		sign = -1.0

	nums = re.findall(r"\d+(?:\.\d+)?", cleaned)
	if not nums:
		raise ValueError(f"Impossible de parser l'angle: {text}")

	deg = float(nums[0])
	minute = float(nums[1]) if len(nums) > 1 else 0.0
	second = float(nums[2]) if len(nums) > 2 else 0.0

	value = deg + minute / 60.0 + second / 3600.0
	value *= sign

	if is_latitude and not (-90.0 <= value <= 90.0):
		raise ValueError(f"Latitude invalide: {value}")
	if not is_latitude and not (-180.0 <= value <= 180.0):
		raise ValueError(f"Longitude invalide: {value}")
	return value


def parse_ra(ra_raw: str) -> float:
	parts = [p.strip() for p in ra_raw.split("|") if p.strip()]
	if len(parts) == 1:
		h = float(parts[0])
		m = 0.0
		s = 0.0
	elif len(parts) == 2:
		h = float(parts[0])
		m = float(parts[1])
		s = 0.0
	else:
		h = float(parts[0])
		m = float(parts[1])
		s = float(parts[2])
	return h + m / 60.0 + s / 3600.0


def parse_dec(dec_raw: str) -> float:
	parts = [p.strip() for p in dec_raw.split("|") if p.strip()]
	if not parts:
		raise ValueError(f"Declinaison invalide: {dec_raw}")

	sign = -1.0 if parts[0].startswith("-") else 1.0
	d = abs(float(parts[0]))
	m = float(parts[1]) if len(parts) > 1 else 0.0
	s = float(parts[2]) if len(parts) > 2 else 0.0
	return sign * (d + m / 60.0 + s / 3600.0)


def load_catalog(path: Path) -> list[MessierObject]:
	objects: list[MessierObject] = []
	with path.open("r", encoding="utf-8") as f:
		reader = csv.DictReader(f, delimiter=";")
		for row in reader:
			name = row["name"].strip()
			common_name = row.get("common_name", "").strip()
			ra_hours = parse_ra(row["ra"].strip())
			dec_deg = parse_dec(row["dec"].strip())
			objects.append(
				MessierObject(
					name=name,
					common_name=common_name,
					ra_hours=ra_hours,
					dec_deg=dec_deg,
				)
			)

	objects.sort(key=lambda x: int(x.name[1:]))
	if len(objects) != 110:
		raise ValueError(
			f"Catalogue incomplet: {len(objects)} objets trouvés (110 attendus)."
		)
	return objects


def julian_day(dt_utc: datetime) -> float:
	if dt_utc.tzinfo is None:
		raise ValueError("La date doit etre timezone-aware UTC")
	return dt_utc.timestamp() / 86400.0 + 2440587.5


def gmst_hours(dt_utc: datetime) -> float:
	d = julian_day(dt_utc) - 2451545.0
	gmst = 18.697374558 + 24.06570982441908 * d
	return normalize_hours(gmst)


def lst_hours(dt_utc: datetime, lon_deg: float) -> float:
	return normalize_hours(gmst_hours(dt_utc) + lon_deg / 15.0)


def local_transit_utc(day: date, ra_hours: float, lon_deg: float) -> datetime:
	midnight = datetime.combine(day, time(0, 0, 0), tzinfo=UTC)
	gmst0 = gmst_hours(midnight)
	delta = normalize_hours(ra_hours - (gmst0 + lon_deg / 15.0))
	ut_hours = delta / 1.00273790935
	return midnight + timedelta(hours=ut_hours)


def horizontal_coordinates(
	dt_utc: datetime, lat_deg: float, lon_deg: float, ra_hours: float, dec_deg: float
) -> tuple[float, float]:
	lat = math.radians(lat_deg)
	dec = math.radians(dec_deg)
	ha_deg = (lst_hours(dt_utc, lon_deg) - ra_hours) * 15.0
	ha_deg = ((ha_deg + 180.0) % 360.0) - 180.0
	ha = math.radians(ha_deg)

	sin_alt = math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(ha)
	sin_alt = max(-1.0, min(1.0, sin_alt))
	alt = math.asin(sin_alt)

	cos_alt = max(1e-12, math.cos(alt))
	sin_az = -math.sin(ha) * math.cos(dec) / cos_alt
	cos_az = (math.sin(dec) - math.sin(alt) * math.sin(lat)) / (cos_alt * math.cos(lat))
	az = math.atan2(sin_az, cos_az)

	alt_deg = math.degrees(alt)
	az_deg = normalize_degrees(math.degrees(az))
	return alt_deg, az_deg


def sun_ra_dec_deg(dt_utc: datetime) -> tuple[float, float]:
	jd = julian_day(dt_utc)
	n = jd - 2451545.0
	l = normalize_degrees(280.460 + 0.9856474 * n)
	g = normalize_degrees(357.528 + 0.9856003 * n)
	g_rad = math.radians(g)

	lambd = normalize_degrees(l + 1.915 * math.sin(g_rad) + 0.020 * math.sin(2.0 * g_rad))
	eps = 23.439 - 0.0000004 * n

	lambd_rad = math.radians(lambd)
	eps_rad = math.radians(eps)

	ra = math.degrees(
		math.atan2(math.cos(eps_rad) * math.sin(lambd_rad), math.cos(lambd_rad))
	)
	ra = normalize_degrees(ra)
	dec = math.degrees(math.asin(math.sin(eps_rad) * math.sin(lambd_rad)))
	return ra, dec


def sun_ecliptic_longitude_deg(dt_utc: datetime) -> float:
	jd = julian_day(dt_utc)
	n = jd - 2451545.0
	l = normalize_degrees(280.460 + 0.9856474 * n)
	g = normalize_degrees(357.528 + 0.9856003 * n)
	g_rad = math.radians(g)
	return normalize_degrees(l + 1.915 * math.sin(g_rad) + 0.020 * math.sin(2.0 * g_rad))


def moon_ra_dec_distance(dt_utc: datetime) -> tuple[float, float, float]:
	# Low-precision geocentric Moon model (adequate for planning outputs).
	jd = julian_day(dt_utc)
	d = jd - 2451543.5

	n = normalize_degrees(125.1228 - 0.0529538083 * d)
	i = 5.1454
	w = normalize_degrees(318.0634 + 0.1643573223 * d)
	a = 60.2666
	e = 0.054900
	m = normalize_degrees(115.3654 + 13.0649929509 * d)

	m_rad = math.radians(m)
	e_anom = m + math.degrees(e * math.sin(m_rad) * (1.0 + e * math.cos(m_rad)))
	e_anom_rad = math.radians(e_anom)

	xv = a * (math.cos(e_anom_rad) - e)
	yv = a * (math.sqrt(1.0 - e * e) * math.sin(e_anom_rad))
	v = math.atan2(yv, xv)
	r = math.sqrt(xv * xv + yv * yv)

	n_rad = math.radians(n)
	i_rad = math.radians(i)
	vw = v + math.radians(w)

	xh = r * (math.cos(n_rad) * math.cos(vw) - math.sin(n_rad) * math.sin(vw) * math.cos(i_rad))
	yh = r * (math.sin(n_rad) * math.cos(vw) + math.cos(n_rad) * math.sin(vw) * math.cos(i_rad))
	zh = r * (math.sin(vw) * math.sin(i_rad))

	lon = math.atan2(yh, xh)
	lat = math.atan2(zh, math.sqrt(xh * xh + yh * yh))

	eps = math.radians(23.4393 - 0.0000004 * d)
	xe = math.cos(lon) * math.cos(lat)
	ye = math.sin(lon) * math.cos(lat)
	ze = math.sin(lat)

	xeq = xe
	yeq = ye * math.cos(eps) - ze * math.sin(eps)
	zeq = ye * math.sin(eps) + ze * math.cos(eps)

	ra_deg = normalize_degrees(math.degrees(math.atan2(yeq, xeq)))
	dec_deg = math.degrees(math.asin(max(-1.0, min(1.0, zeq))))
	return ra_deg / 15.0, dec_deg, r


def angular_separation_deg(ra1_hours: float, dec1_deg: float, ra2_hours: float, dec2_deg: float) -> float:
	ra1 = math.radians(ra1_hours * 15.0)
	ra2 = math.radians(ra2_hours * 15.0)
	dec1 = math.radians(dec1_deg)
	dec2 = math.radians(dec2_deg)

	cos_sep = math.sin(dec1) * math.sin(dec2) + math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
	cos_sep = max(-1.0, min(1.0, cos_sep))
	return math.degrees(math.acos(cos_sep))


def moon_phase_age_and_illumination(dt_utc: datetime, moon_ra_hours: float, moon_dec_deg: float) -> tuple[float, float]:
	sun_lon = sun_ecliptic_longitude_deg(dt_utc)
	moon_lon = moon_ecliptic_longitude_deg(dt_utc)
	delta_lon = normalize_degrees(moon_lon - sun_lon)
	age_days = SYNODIC_MONTH_DAYS * delta_lon / 360.0

	sun_ra_deg, sun_dec_deg = sun_ra_dec_deg(dt_utc)
	sep = angular_separation_deg(moon_ra_hours, moon_dec_deg, sun_ra_deg / 15.0, sun_dec_deg)
	illumination = (1.0 - math.cos(math.radians(sep))) / 2.0
	return age_days, illumination * 100.0


def moon_ecliptic_longitude_deg(dt_utc: datetime) -> float:
	jd = julian_day(dt_utc)
	d = jd - 2451543.5

	n = normalize_degrees(125.1228 - 0.0529538083 * d)
	i = 5.1454
	w = normalize_degrees(318.0634 + 0.1643573223 * d)
	a = 60.2666
	e = 0.054900
	m = normalize_degrees(115.3654 + 13.0649929509 * d)

	m_rad = math.radians(m)
	e_anom = m + math.degrees(e * math.sin(m_rad) * (1.0 + e * math.cos(m_rad)))
	e_anom_rad = math.radians(e_anom)

	xv = a * (math.cos(e_anom_rad) - e)
	yv = a * (math.sqrt(1.0 - e * e) * math.sin(e_anom_rad))
	v = math.atan2(yv, xv)
	r = math.sqrt(xv * xv + yv * yv)

	n_rad = math.radians(n)
	i_rad = math.radians(i)
	vw = v + math.radians(w)

	xh = r * (math.cos(n_rad) * math.cos(vw) - math.sin(n_rad) * math.sin(vw) * math.cos(i_rad))
	yh = r * (math.sin(n_rad) * math.cos(vw) + math.cos(n_rad) * math.sin(vw) * math.cos(i_rad))
	return normalize_degrees(math.degrees(math.atan2(yh, xh)))


def sun_altitude_deg(dt_utc: datetime, lat_deg: float, lon_deg: float) -> float:
	sun_ra_deg, sun_dec_deg = sun_ra_dec_deg(dt_utc)
	sun_ra_hours = sun_ra_deg / 15.0
	alt_deg, _ = horizontal_coordinates(dt_utc, lat_deg, lon_deg, sun_ra_hours, sun_dec_deg)
	return alt_deg


def find_astronomical_night(
	day: date, lat_deg: float, lon_deg: float
) -> tuple[datetime | None, datetime | None, bool]:
	start = datetime.combine(day, time(12, 0, 0), tzinfo=UTC)
	end = start + timedelta(hours=24)
	step = timedelta(minutes=10)

	samples: list[tuple[datetime, float]] = []
	t = start
	while t <= end:
		samples.append((t, sun_altitude_deg(t, lat_deg, lon_deg)))
		t += step

	crossings: list[tuple[datetime, str]] = []
	for i in range(len(samples) - 1):
		t1, a1 = samples[i]
		t2, a2 = samples[i + 1]
		d1 = a1 - TARGET_SUN_ALT
		d2 = a2 - TARGET_SUN_ALT

		if d1 == 0.0:
			kind = "down" if a2 < a1 else "up"
			crossings.append((t1, kind))
			continue

		if d1 * d2 < 0.0:
			frac = (TARGET_SUN_ALT - a1) / (a2 - a1)
			tc = t1 + (t2 - t1) * frac
			kind = "down" if a2 < a1 else "up"
			crossings.append((tc, kind))

	dusk = None
	dawn = None
	for tc, kind in crossings:
		if kind == "down":
			dusk = tc
			break

	if dusk is not None:
		for tc, kind in crossings:
			if kind == "up" and tc > dusk:
				dawn = tc
				break

	if dusk is not None and dawn is not None:
		return dusk, dawn, True

	all_dark = all(alt <= TARGET_SUN_ALT for _, alt in samples)
	all_bright = all(alt > TARGET_SUN_ALT for _, alt in samples)

	if all_dark:
		return start, end, True
	if all_bright:
		return None, None, False
	return dusk, dawn, False


def azimuth_to_cardinal(az_deg: float) -> str:
	dirs = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
	idx = int((az_deg + 22.5) // 45.0) % 8
	return dirs[idx]


def is_transit_visible_at_night(
	transit_utc: datetime,
	altitude_deg: float,
	dusk: datetime | None,
	dawn: datetime | None,
	has_night: bool,
) -> bool:
	if altitude_deg <= 0.0:
		return False
	if not has_night or dusk is None or dawn is None:
		return False
	return dusk <= transit_utc <= dawn


def iter_days(year: int):
	current = date(year, 1, 1)
	end = date(year + 1, 1, 1)
	while current < end:
		yield current
		current += timedelta(days=1)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description=(
			"Calcule, pour chaque jour d'une annee et chaque objet Messier, "
			"l'heure UTC de culmination, altitude/azimut et visibilite pendant la nuit astronomique."
		)
	)
	parser.add_argument("--year", type=int, required=True, help="Annee a calculer (ex: 2026)")
	parser.add_argument(
		"--latitude",
		required=True,
		help="Latitude observateur (decimal ou DMS, ex: '49 07 00 N' ou '49.1167')",
	)
	parser.add_argument(
		"--longitude",
		required=True,
		help="Longitude observateur (decimal ou DMS, ex: '2 18 00 E' ou '2.3')",
	)
	parser.add_argument(
		"--altitude-m",
		type=float,
		default=0.0,
		help="Altitude observateur en metres (informative)",
	)
	parser.add_argument(
		"--catalog",
		default="messier_catalog.csv",
		help="Chemin du catalogue Messier CSV (name;common_name;ra;dec)",
	)
	parser.add_argument(
		"--output",
		default=None,
		help="Chemin du fichier CSV de sortie. Defaut: messier_zenith_<annee>.csv",
	)
	parser.add_argument(
		"--resume",
		action="store_true",
		help=(
			"Mode resume: n'exporte que les lignes ou l'objet est visible la nuit "
			"(culmination entre coucher et lever astronomiques)."
		),
	)
	return parser


def run_generation(args: argparse.Namespace) -> Path:

	lat_deg = parse_angle(args.latitude, is_latitude=True)
	lon_deg = parse_angle(args.longitude, is_latitude=False)

	catalog_path = Path(args.catalog)
	if not catalog_path.exists():
		raise FileNotFoundError(f"Catalogue introuvable: {catalog_path}")

	objects = load_catalog(catalog_path)
	if args.output:
		output_path = Path(args.output)
	else:
		suffix = "resume_" if args.resume else ""
		output_path = Path(f"messier_zenith_{suffix}{args.year}.csv")

	header = [
		"object",
		"common_name",
		"date",
		"utc_time",
		"altitude_deg",
		"azimuth_deg",
		"direction",
		"visible_at_night",
		"moon_up",
		"moon_age_days",
		"moon_illumination_pct",
		"moon_object_distance_deg",
	]

	with output_path.open("w", newline="", encoding="utf-8-sig") as f:
		writer = csv.writer(f, delimiter=";")
		writer.writerow(header)
		print(";".join(header))

		for day in iter_days(args.year):
			dusk, dawn, has_night = find_astronomical_night(day, lat_deg, lon_deg)

			for obj in objects:
				transit = local_transit_utc(day, obj.ra_hours, lon_deg)
				alt_deg, az_deg = horizontal_coordinates(
					transit, lat_deg, lon_deg, obj.ra_hours, obj.dec_deg
				)
				moon_ra_hours, moon_dec_deg, _ = moon_ra_dec_distance(transit)
				moon_alt_deg, _ = horizontal_coordinates(
					transit, lat_deg, lon_deg, moon_ra_hours, moon_dec_deg
				)
				moon_is_up = moon_alt_deg > 0.0
				moon_age_days, moon_illumination_pct = moon_phase_age_and_illumination(
					transit, moon_ra_hours, moon_dec_deg
				)
				moon_object_sep_deg = angular_separation_deg(
					obj.ra_hours, obj.dec_deg, moon_ra_hours, moon_dec_deg
				)
				cardinal = azimuth_to_cardinal(az_deg)
				visible = is_transit_visible_at_night(transit, alt_deg, dusk, dawn, has_night)

				row = [
					obj.name,
					obj.common_name,
					day.isoformat(),
					transit.strftime("%H:%M:%S"),
					f"{alt_deg:.2f}",
					f"{az_deg:.2f}",
					cardinal,
					"Oui" if visible else "Non",
					"Oui" if moon_is_up else "Non",
					f"{moon_age_days:.2f}",
					f"{moon_illumination_pct:.1f}",
					f"{moon_object_sep_deg:.2f}",
				]

				if args.resume and not visible:
					continue

				writer.writerow(row)
				print(";".join(row))

	print(
		f"\nFichier genere: {output_path} | annee={args.year} | latitude={lat_deg:.6f} | "
		f"longitude={lon_deg:.6f} | altitude_m={args.altitude_m:.1f}"
	)
	return output_path


def launch_gui() -> int:
	try:
		import tkinter as tk
		from tkinter import messagebox
	except Exception as exc:
		print(f"Tkinter indisponible: {exc}")
		print("Veuillez utiliser les arguments CLI (--help) pour lancer le calcul.")
		return 2

	texts = {
		"fr": {
			"title": "Messier - Parametres de calcul",
			"language": "Langue",
			"year": "Annee",
			"year_help": "Annee complete a calculer, par exemple: 2026",
			"latitude": "Latitude",
			"latitude_help": "Position Nord/Sud en decimal ou DMS. Ex: 49.1167 ou 49 07 00 N",
			"longitude": "Longitude",
			"longitude_help": "Position Est/Ouest en decimal ou DMS. Ex: 2.3 ou 2 18 00 E",
			"altitude": "Altitude (m)",
			"altitude_help": "Altitude du lieu en metres (optionnel). Defaut: 0",
			"catalog": "Fichier catalogue",
			"catalog_help": "CSV source des objets Messier (name;common_name;ra;dec)",
			"output": "Fichier de sortie",
			"output_help": "Chemin CSV resultat. Vide = nom automatique",
			"resume": "Mode resume",
			"resume_help": "Si coche: exporte seulement les objets visibles la nuit",
			"run": "Lancer le calcul",
			"ok_title": "Termine",
			"ok_msg": "Calcul termine. Fichier genere:\n{path}",
			"error_title": "Erreur",
			"required": "Les champs Annee, Latitude et Longitude sont obligatoires.",
			"running": "Calcul en cours...",
			"ready": "Pret",
		},
		"en": {
			"title": "Messier - Calculation Parameters",
			"language": "Language",
			"year": "Year",
			"year_help": "Full year to compute, for example: 2026",
			"latitude": "Latitude",
			"latitude_help": "North/South position in decimal or DMS. Ex: 49.1167 or 49 07 00 N",
			"longitude": "Longitude",
			"longitude_help": "East/West position in decimal or DMS. Ex: 2.3 or 2 18 00 E",
			"altitude": "Altitude (m)",
			"altitude_help": "Observer altitude in meters (optional). Default: 0",
			"catalog": "Catalog file",
			"catalog_help": "Source Messier CSV (name;common_name;ra;dec)",
			"output": "Output file",
			"output_help": "Result CSV path. Empty = automatic name",
			"resume": "Summary mode",
			"resume_help": "If checked: export only objects visible at night",
			"run": "Run calculation",
			"ok_title": "Done",
			"ok_msg": "Calculation complete. Generated file:\n{path}",
			"error_title": "Error",
			"required": "Year, Latitude and Longitude are required.",
			"running": "Calculation in progress...",
			"ready": "Ready",
		},
	}

	root = tk.Tk()
	root.geometry("860x510")
	root.resizable(True, True)

	lang_var = tk.StringVar(value="fr")

	labels: dict[str, tk.Label] = {}
	help_labels: dict[str, tk.Label] = {}

	values = {
		"year": tk.StringVar(value=str(date.today().year)),
		"latitude": tk.StringVar(value=""),
		"longitude": tk.StringVar(value=""),
		"altitude_m": tk.StringVar(value="0"),
		"catalog": tk.StringVar(value="messier_catalog.csv"),
		"output": tk.StringVar(value=""),
		"resume": tk.BooleanVar(value=False),
	}

	language_frame = tk.Frame(root)
	language_frame.pack(fill="x", padx=12, pady=(12, 6))
	language_label = tk.Label(language_frame, anchor="w")
	language_label.pack(side="left")
	language_menu = tk.OptionMenu(language_frame, lang_var, "fr", "en")
	language_menu.pack(side="left", padx=(10, 0))

	form = tk.Frame(root)
	form.pack(fill="both", expand=True, padx=12, pady=6)
	form.grid_columnconfigure(1, weight=1)

	rows = [
		("year", values["year"]),
		("latitude", values["latitude"]),
		("longitude", values["longitude"]),
		("altitude", values["altitude_m"]),
		("catalog", values["catalog"]),
		("output", values["output"]),
	]

	for idx, (key, var) in enumerate(rows):
		row_offset = idx * 2
		labels[key] = tk.Label(form, anchor="w", width=20)
		labels[key].grid(row=row_offset, column=0, sticky="w", pady=(4, 0))
		entry = tk.Entry(form, textvariable=var)
		entry.grid(row=row_offset, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))

		help_labels[key] = tk.Label(form, anchor="w", justify="left", fg="#4d4d4d")
		help_labels[key].grid(row=row_offset + 1, column=0, columnspan=2, sticky="w", pady=(0, 4))

	resume_row = len(rows) * 2
	resume_check = tk.Checkbutton(form, variable=values["resume"], anchor="w", justify="left")
	resume_check.grid(row=resume_row, column=0, columnspan=2, sticky="w", pady=(10, 0))
	help_labels["resume"] = tk.Label(form, anchor="w", justify="left", fg="#4d4d4d")
	help_labels["resume"].grid(row=resume_row + 1, column=0, columnspan=2, sticky="w", pady=(0, 8))

	footer = tk.Frame(root)
	footer.pack(fill="x", padx=12, pady=(0, 12))
	status_var = tk.StringVar(value="")
	status = tk.Label(footer, textvariable=status_var, anchor="w")
	status.pack(side="left")
	run_button = tk.Button(footer)
	run_button.pack(side="right")

	def t(key: str) -> str:
		return texts[lang_var.get()][key]

	def refresh_ui() -> None:
		root.title(t("title"))
		language_label.config(text=f"{t('language')}: ")
		labels["year"].config(text=t("year"))
		help_labels["year"].config(text=t("year_help"))
		labels["latitude"].config(text=t("latitude"))
		help_labels["latitude"].config(text=t("latitude_help"))
		labels["longitude"].config(text=t("longitude"))
		help_labels["longitude"].config(text=t("longitude_help"))
		labels["altitude"].config(text=t("altitude"))
		help_labels["altitude"].config(text=t("altitude_help"))
		labels["catalog"].config(text=t("catalog"))
		help_labels["catalog"].config(text=t("catalog_help"))
		labels["output"].config(text=t("output"))
		help_labels["output"].config(text=t("output_help"))
		resume_check.config(text=t("resume"))
		help_labels["resume"].config(text=t("resume_help"))
		run_button.config(text=t("run"))
		if not status_var.get() or status_var.get() in {
			texts["fr"]["ready"],
			texts["en"]["ready"],
			texts["fr"]["running"],
			texts["en"]["running"],
		}:
			status_var.set(t("ready"))

	def on_run() -> None:
		year_raw = values["year"].get().strip()
		latitude_raw = values["latitude"].get().strip()
		longitude_raw = values["longitude"].get().strip()
		altitude_raw = values["altitude_m"].get().strip()
		catalog_raw = values["catalog"].get().strip() or "messier_catalog.csv"
		output_raw = values["output"].get().strip()

		if not year_raw or not latitude_raw or not longitude_raw:
			messagebox.showerror(t("error_title"), t("required"))
			return

		try:
			args = argparse.Namespace(
				year=int(year_raw),
				latitude=latitude_raw,
				longitude=longitude_raw,
				altitude_m=float(altitude_raw or "0"),
				catalog=catalog_raw,
				output=output_raw or None,
				resume=bool(values["resume"].get()),
			)
		except ValueError as exc:
			messagebox.showerror(t("error_title"), str(exc))
			return

		run_button.config(state="disabled")
		status_var.set(t("running"))
		root.update_idletasks()

		try:
			output_path = run_generation(args)
		except Exception as exc:
			messagebox.showerror(t("error_title"), str(exc))
		else:
			messagebox.showinfo(t("ok_title"), t("ok_msg").format(path=output_path))
		finally:
			run_button.config(state="normal")
			status_var.set(t("ready"))

	lang_var.trace_add("write", lambda *_: refresh_ui())
	run_button.config(command=on_run)
	refresh_ui()

	root.mainloop()
	return 0


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	cli_args = sys.argv[1:] if argv is None else argv
	if not cli_args:
		return launch_gui()

	args = parser.parse_args(cli_args)
	run_generation(args)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
