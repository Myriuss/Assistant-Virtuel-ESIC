import csv
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from io import StringIO

sys.path.append("/app")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import TimetableSlot

CSV_PATH = Path(os.getenv("TIMETABLE_PATH", "/data/raw/emploi_du_temps_exclusive.csv"))
JSON_PATH = Path(os.getenv("TIMETABLE_JSON_PATH", "/data/raw/emploi_du_temps.json"))

SEMESTER_START_MONDAY = date(2025, 9, 22)

DAYS = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}

def build_datetime(jour: str, heure_str: str) -> datetime:
    jour_norm = (jour or "").strip().lower()
    idx = DAYS[jour_norm]
    base_date = SEMESTER_START_MONDAY.toordinal() + idx
    d = date.fromordinal(base_date)
    h = datetime.strptime(heure_str.strip(), "%H:%M").time()
    return datetime.combine(d, h)

def clean_line(line: str) -> str:
    line = line.rstrip("\r\n")
    line = line.rstrip(";")
    line = line.lstrip(";")
    return line

def fix_mojibake(s: str) -> str:
    """
    Corrige les chaînes genre 'Introduction Ã la Programmation' -> 'Introduction à la Programmation'.
    Cas typique : texte UTF‑8 qui a été interprété comme latin‑1.
    """
    if not s:
        return s
    try:
        # on part de la chaîne affichée moche, on la considère comme latin‑1,
        # puis on la lit comme utf‑8 réelle
        return s.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return s

def apply_exam_dates_from_json(db: Session, json_path: Path = JSON_PATH) -> None:
    if not json_path.exists():
        print(f"[WARN] JSON file not found: {json_path}")
        return

    data = json.loads(json_path.read_text(encoding="utf-8"))
    semestres = data.get("metadata", {}).get("semestres", [])

    updated = 0
    for sem in semestres:
        semestre_code = sem.get("semestre")      # "S1", "S2", ...
        exams = sem.get("examens")
        if not semestre_code or not exams:
            continue

        debut = date.fromisoformat(exams["debut"])
        fin = date.fromisoformat(exams["fin"])

        # Mettre à jour tous les slots de ce semestre
        res = (
            db.query(TimetableSlot)
            .filter(TimetableSlot.semester == semestre_code)
            .update(
                {
                    TimetableSlot.exam_start: debut,
                    TimetableSlot.exam_end: fin,
                },
                synchronize_session=False,
            )
        )
        updated += res
        print(f"[OK] Updated exam dates for semester {semestre_code}: {debut} -> {fin} ({res} rows)")

    db.commit()
    print(f"[OK] Total rows updated with exam dates: {updated}")

def main(csv_path: Path = CSV_PATH):
    db: Session = SessionLocal()
    try:
        inserted = 0

        # 1) Lecture simple en texte (tel que Python voit le fichier)
        #    On garde l'encodage système ou utf-8, peu importe pour la suite
        with csv_path.open("r", encoding="utf-8", errors="replace") as f:
            raw_lines = [clean_line(l) for l in f]

        # 2) En-tête + données
        header_line = raw_lines[2]
        data_lines = raw_lines[3:]

        csv_text = header_line + "\n" + "\n".join(data_lines)
        buf = StringIO(csv_text)

        reader = csv.DictReader(buf, delimiter=",")
        print("FIELDS:", reader.fieldnames)

        for i, row in enumerate(reader, start=1):
            if i <= 3:
                print("ROW", i, row)

            if not row.get("formation"):
                continue

            # appliquer fix_mojibake sur tous les champs texte
            formation = fix_mojibake(row.get("formation", "").strip())
            groupe = fix_mojibake(row.get("groupe", "").strip())
            semestre = fix_mojibake(row.get("semestre", "").strip())

            jour = fix_mojibake(row.get("jour", "").strip())
            start_dt = build_datetime(jour, row["heure_debut"])
            end_dt = build_datetime(jour, row["heure_fin"])

            mat_code = fix_mojibake(row.get("matiere_code", "").strip())
            mat_nom = fix_mojibake(row.get("matiere_nom", "").strip())
            type_cours = fix_mojibake(row.get("type_cours", "").strip())

            course = f"{mat_code} - {mat_nom} ({type_cours})".strip(" -()")

            enseignant_id = fix_mojibake(row.get("enseignant_id", "").strip())
            enseignant_nom = fix_mojibake(row.get("enseignant_nom", "").strip())

            salle_code = fix_mojibake(row.get("salle_code", "").strip())
            salle_nom = fix_mojibake(row.get("salle_nom", "").strip())
            batiment = fix_mojibake(row.get("batiment", "").strip())

            room_parts = [salle_nom, salle_code, batiment]
            room = " ".join(p for p in room_parts if p)

            slot = TimetableSlot(
                program=formation or None,
                group_name=groupe or None,
                semester=semestre or None,
                subject_code=mat_code or None,
                subject_name=mat_nom or None,
                course_type=type_cours or None,
                teacher_id=enseignant_id or None,
                teacher=enseignant_nom or None,
                room_code=salle_code or None,
                room_name=salle_nom or None,
                building=batiment or None,
                day=jour or None,
                start_time=start_dt,
                end_time=end_dt,
                raw={k: fix_mojibake(v) if isinstance(v, str) else v for k, v in row.items()},
            )
            db.add(slot)
            inserted += 1

        db.commit()
        print(f"[OK] Inserted timetable slots: {inserted}")
        apply_exam_dates_from_json(db)
    finally:
        db.close()

if __name__ == "__main__":
    main()
