# SCRATCHPAD — retours utilisateur d'octobre 2026

Stories validées le 14/10/2026, un commit par lot. Détail des décisions dans
la conversation ; ici, seulement l'état d'avancement.

| Lot | Contenu | État |
|-----|---------|------|
| A | Équipement par plante, cumulé avec l'emplacement | fait |
| B | Journal parasitaire : inspection / traitement séparés, champ tags, épisode déduit du journal, filtre « Parasitées » | fait |
| D | Déclarer une bouture depuis la plante mère (+ entrée Bouturage chez la mère) | à faire |
| E | Supprimer emplacement, pot, plante (avec « Déclarer morte » à la place) | à faire |
| C | Créer / modifier une espèce, détection de ressemblance (difflib, 85 %), création à la volée depuis l'ajout de plante | à faire |

Hors périmètre, décidé : pas de page globale des parasitées, pas d'import GBIF
en direct, pas de traitements répétés en règles de soin, une bouture à la fois.

Migration unique : `0007_plant_equipment_pest_journal` (à lancer par Romain).
Script à relancer : `populate_abiotic_database` (action TREAT_PESTS).
