import json
import os
import sys
from typing import Any, Dict, Optional

sys.path.append("/app")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Contact

RAW_PATH = os.getenv("CONTACTS_PATH", "/data/raw/annuaire_contacts.json")

SERVICE_KEYS = {"service", "departement", "department", "pole", "pôle", "bureau", "direction"}
NAME_KEYS = {"name", "nom", "contact", "responsable"}
EMAIL_KEYS = {"email", "mail"}
PHONE_KEYS = {"phone", "tel", "telephone", "téléphone", "mobile"}
LOC_BATIMENT_KEYS = {"batiment", "bâtiment", "building"}
LOC_BUREAU_KEYS = {"bureau", "office", "salle"}
HOURS_KEYS = {"hours", "horaires", "horaire"}
FORMATION_KEYS = {"formation", "programme"}
COMMENT_KEYS = {"description", "missions"}


def _get_str(d: Dict[str, Any], keys: set) -> Optional[str]:
    for k in list(d.keys()):
        if k in keys and d.get(k) is not None:
            v = d.get(k)
            if isinstance(v, str):
                s = v.strip()
                return s if s else None
        if k in keys and isinstance(d.get(k), list):
            vals = [x.strip() for x in d[k] if isinstance(x, str) and x.strip()]
            if vals:
                return "; ".join(vals)
    lower = {k.lower(): k for k in d.keys()}
    for kk in keys:
        if kk.lower() in lower:
            v = d.get(lower[kk.lower()])
            if isinstance(v, str):
                s = v.strip()
                return s if s else None
    return None


def _build_nom_complet(d: Dict[str, Any]) -> Optional[str]:
    nom = d.get("nom") or d.get("last_name")
    prenom = d.get("prenom") or d.get("first_name")
    if isinstance(nom, str) and isinstance(prenom, str):
        nom = nom.strip()
        prenom = prenom.strip()
        if nom or prenom:
            return f"{prenom} {nom}".strip()
    v = d.get("name")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _detect_categorie_principale(root_key: str) -> str:
    if root_key == "direction":
        return "Direction"
    if root_key == "services_administratifs":
        return "Services administratifs"
    if root_key == "services_etudiants":
        return "Services étudiants"
    if root_key == "responsables_pedagogiques":
        return "Responsables pédagogiques"
    if root_key == "enseignants":
        return "Enseignants"
    if root_key == "delegues_etudiants":
        return "Délégués étudiants"
    if root_key == "associations_etudiantes":
        return "Associations étudiantes"
    if root_key == "contacts_urgence":
        return "Contacts d'urgence"
    if root_key == "partenaires_externes":
        return "Partenaires externes"
    return "Annuaire"


def _ingest_node(
    db: Session,
    node: Any,
    root_key: str,
    current_service: Optional[str] = None,
    current_formation: Optional[str] = None,
    current_hours: Optional[str] = None,
):
    """
    Parcourt récursivement un sous-arbre en gardant le contexte :
    - root_key : bloc racine (direction, services_administratifs, ...)
    - current_service : valeur de 'service' la plus proche dans l'arbre (ex: "Scolarité")
    - current_formation : valeur de 'formation' la plus proche (ex: "Master 1 - IA")
    """
    if isinstance(node, dict):
        # mise à jour du contexte service si ce dict a un champ 'service'
        service_val = _get_str(node, {"service"})
        if service_val:
            current_service = service_val

        # mise à jour du contexte formation si ce dict a un champ 'formation'
        formation_val = _get_str(node, {"formation"})
        if formation_val:
            current_formation = formation_val

        # mise à jour du contexte horaires si ce dict a un champ 'horaires'
        hours_val = _get_str(node, HOURS_KEYS)
        if hours_val:
            current_hours = hours_val
        categorie_principale = _detect_categorie_principale(root_key)
        # construire un Contact si on a suffisamment d'infos
        email = _get_str(node, EMAIL_KEYS)
        telephone = _get_str(node, PHONE_KEYS)
        nom_complet = _build_nom_complet(node)

        if email or telephone or nom_complet:
            sous_categorie = current_service
            role = None

            type_contact = "Personne"
            if node.get("service") or node.get("organisme"):
                type_contact = "Service"
            if "president" in node:
                type_contact = "Association"

            batiment = _get_str(node, LOC_BATIMENT_KEYS)
            bureau = _get_str(node, LOC_BUREAU_KEYS)
            horaires_local = _get_str(node, HOURS_KEYS)
            horaires = horaires_local or current_hours

            # hérite de la formation parente (ex: "Master 1 - IA")
            formations_public = current_formation

            # matières / spécialité (enseignants)
            matieres = None
            if isinstance(node.get("matieres"), list):
                vals = [m for m in node["matieres"] if isinstance(m, str) and m.strip()]
                if vals:
                    matieres = "; ".join(vals)
            specialite = node.get("specialite")
            if isinstance(specialite, str) and specialite.strip():
                matieres = specialite.strip() + (f" : {matieres}" if matieres else "")

            commentaires = _get_str(node, COMMENT_KEYS)

            contact = Contact(
                categorie_principale=categorie_principale,
                sous_categorie=sous_categorie,
                role=role,
                nom_complet=nom_complet,
                type_contact=type_contact,
                email=email,
                telephone=telephone,
                batiment=batiment,
                bureau=bureau,
                horaires=horaires,
                formations_public=formations_public,
                matieres_specialite=matieres,
                statut=None,
                commentaires=commentaires,
            )
            db.add(contact)
        if isinstance(node.get("responsable"), dict) and current_service:
            resp_dict = node["responsable"]
            resp_email = _get_str(resp_dict, EMAIL_KEYS)
            resp_tel = _get_str(resp_dict, PHONE_KEYS)
            resp_nom = _build_nom_complet(resp_dict)

            if resp_email or resp_tel or resp_nom:
                sous_categorie = current_service
                role = f"Responsable {current_service}"

                batiment = _get_str(node, LOC_BATIMENT_KEYS)
                bureau = _get_str(node, LOC_BUREAU_KEYS)
                horaires = _get_str(node, HOURS_KEYS) or current_hours

                contact = Contact(
                    categorie_principale=categorie_principale,
                    sous_categorie=sous_categorie,
                    role=role,
                    nom_complet=resp_nom,
                    type_contact="Personne",
                    email=resp_email,
                    telephone=resp_tel,
                    batiment=batiment,
                    bureau=bureau,
                    horaires=horaires,
                    formations_public=current_formation,
                    matieres_specialite=None,
                    statut=None,
                    commentaires=_get_str(node, COMMENT_KEYS),
                )
                db.add(contact)

        # descente récursive
        for v in node.values():
            _ingest_node(
                db,
                v,
                root_key=root_key,
                current_service=current_service,
                current_formation=current_formation,
                current_hours=current_hours,
            )

    elif isinstance(node, list):
        for it in node:
            _ingest_node(
                db,
                it,
                root_key=root_key,
                current_service=current_service,
                current_formation=current_formation,
                current_hours=current_hours,
            )


def main():
    db: Session = SessionLocal()
    try:
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        inserted_before = db.query(Contact).count()

        for root_key, root_value in data.items():
            _ingest_node(db, root_value, root_key=root_key, current_service=None, current_formation=None, current_hours=None,)

        db.commit()

        inserted_after = db.query(Contact).count()
        inserted = inserted_after - inserted_before
        print(f"[OK] Contacts inserted: {inserted} | file: {RAW_PATH}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
