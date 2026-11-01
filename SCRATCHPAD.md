# SCRATCHPAD — retours utilisateur d'octobre 2026

Stories validées le 14/10/2026, un commit par lot. Tout est livré le 14/10/2026 ;
reste à Romain : lancer la migration et le script, puis déployer. Détail des décisions dans
la conversation ; ici, seulement l'état d'avancement.

| Lot | Contenu | État |
|-----|---------|------|
| A | Équipement par plante, cumulé avec l'emplacement | fait |
| B | Journal parasitaire : inspection / traitement séparés, champ tags, épisode déduit du journal, filtre « Parasitées » | fait |
| D | Déclarer une bouture depuis la plante mère (+ entrée Bouturage chez la mère) | fait |
| E | Supprimer emplacement, pot, plante (avec « Déclarer morte » à la place) | fait |
| C | Créer / modifier une espèce, détection de ressemblance (difflib, 85 %), création à la volée depuis l'ajout de plante | fait |

Hors périmètre, décidé : pas de page globale des parasitées, pas d'import GBIF
en direct, pas de traitements répétés en règles de soin, une bouture à la fois.

Migration unique : `0007_plant_equipment_pest_journal` (à lancer par Romain).
Script à relancer : `populate_abiotic_database` (action TREAT_PESTS).

## Lot du 26/10/2026

| Lot | Contenu | État |
|-----|---------|------|
| F | `Specie.abiotic_conditions` : notes en texte libre, lues (pas dupliquées) sur la fiche de chaque plante | fait |
| G | Modèle `Room` (nom, description), clé `Spot.room` nullable ; page « Pièces », boîte de création rapide depuis l'emplacement | fait |
| H | Menu « Plante mère » : « Surnom · Nom commun » (`Plant.choice_label`) | fait |
| I | Pièce créable depuis la boîte « Nouvel emplacement » du formulaire plante (boîtes empilées) | fait |
| J | « Mes plantes » : recherche, filtres pièce / emplacement, tri (`PLANT_SORTS`), paramètres dans l'URL | fait |
| K | Journal : bouton « Prendre une photo » (champ `capture` caché recopié dans le champ photo) | fait |

Décision : la pièce est portée par l'emplacement, pas par la plante (une étagère est
dans une pièce ; la pièce d'une plante se déduit). Les emplacements existants sont à
rattacher à la main.

Migration unique : `0008_room_specie_notes` (à lancer par Romain). Commit et push par Romain.

## Lot du 01/11/2026

| Lot | Contenu | État |
|-----|---------|------|
| L | Formulaire plante : pièce d'abord, puis emplacements de cette pièce (filtre côté navigateur, `room_spots.js`), pièce créable à la volée à côté | fait |

Pas de migration : `PlantForm.room` n'est pas un champ du modèle. Pièce sans emplacement
refusée (la plante n'a pas de pièce à elle, le choix serait perdu). Pas d'endpoint : chaque
option d'emplacement porte sa pièce (`data-room`).
| M | Onglet « Entretien » : une action et ses options, un commentaire, les plantes cochées par pièce · emplacement (case par groupe, case « tout »), précisions par plante (options, commentaire, état, mesures, photo) ; une entrée de journal par plante | fait |

Entretien : pas de modèle, tout passe par `PlantHistory`. Les précisions sont un gabarit `<template>`
cloné à la demande (`care_bulk.js`, préfixe `p__` → `p<id>`), sinon cent plantes × tous les champs de
toutes les actions chargeraient la page pour rien. Les précisions sont préremplies du commun et font
foi pour la plante (champ caché `p<id>-refined`) ; un champ jamais touché suit le commun. Les plantes
n'apparaissent qu'une fois l'action choisie. Les mortes ne sont pas proposées. Pas de migration.
