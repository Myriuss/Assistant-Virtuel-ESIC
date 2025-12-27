#!/usr/bin/env bash
set -euo pipefail

API_URL="http://localhost:8000/chat"
USER_ID="test-user"
CHANNEL="web"

questions=(
"Quels sont mes cours lundi ?"
"Où se trouve le cours de Machine Learning ?"
"Qui enseigne la Cybersécurité en B3 ?"
"Quand sont les examens de S1 ?"
"Comment contacter le service scolarité ?"
"Quel est l'email du responsable de Master IA ?"
"Quels sont les horaires de la bibliothèque ?"
"Qui est l'enseignant de Machine Learning ?"
"Comment joindre l'infirmerie ?"
"Numéro d'urgence campus ?"
"Où puis-je consulter mon emploi du temps ?"
"Quand commence le semestre 1 ?"
"Quand commence le semestre 2 ?"
"Quelles sont les dates des vacances scolaires ?"
"Quand ont lieu les examens ?"
"Combien d'heures de cours par semaine ?"
"Mon emploi du temps a changé, comment suis-je informé ?"
"Comment puis-je réserver une salle ?"
"À quelle heure commencent les cours le matin ?"
"Jusqu'à quelle heure y a-t-il des cours ?"
"Y a-t-il cours le samedi ?"
"Où se trouve ma salle de cours ?"
"Comment puis-je exporter mon emploi du temps sur mon téléphone ?"
"Qui dois-je contacter si j'ai un problème avec mon emploi du temps ?"
"Quand a lieu la journée d'intégration ?"
"Quand a lieu le forum des entreprises ?"
"Y a-t-il une permanence de mon responsable de formation ?"
"Combien de temps durent les cours ?"
"Quelle est la différence entre CM, TD et TP ?"
"Puis-je avoir un emploi du temps aménagé ?"
"Comment fonctionne le planning des projets ?"
"Quand dois-je choisir ma spécialisation ?"
"Y a-t-il des examens blancs ?"
"Combien de temps durent les examens ?"
"Puis-je arriver en retard à un examen ?"
"Que se passe-t-il si je suis malade le jour d'un examen ?"
"Quand aurons-nous les résultats des examens ?"
"Comment sont organisées les soutenances de projet ?"
"Y a-t-il des cours pendant les vacances ?"
"Quels sont les jours fériés pendant l'année ?"
"Comment connaître la salle d'examen ?"
"Comment fonctionne le système de rattrapage ?"
"Combien d'absences sont tolérées ?"
"Puis-je partir en vacances avant la fin du semestre ?"
"Quand se déroule la semaine de révisions ?"
"Y a-t-il des cours en ligne ou en distanciel ?"
"Quand sont les soutenances de stage ?"
"Comment fonctionne le système ECTS ?"
)

for q in "${questions[@]}"; do
  echo -e "\033[36mQUESTION:\033[0m $q"

  payload=$(cat <<EOF
{
  "user_id": "$USER_ID",
  "message": "$q",
  "channel": "$CHANNEL"
}
EOF
)

  curl -sS -X POST "$API_URL" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "$payload" || echo -e "\033[31mERREUR HTTP\033[0m"

  echo -e "\n"
  sleep 7
done
