# Sokoban — Édition Pédagogique

Adaptation pédagogique du jeu de puzzle classique Sokoban, conçue pour une utilisation en classe.
Les élèves s'identifient par leur prénom, jouent en mode entraînement ou en tournoi chronométré,
et l'enseignant dispose d'un panneau protégé par code pour suivre les progrès et rejouer les parties.

## Pré-requis & Installation

- Python 3.8 (Windows 7 compatible)
- Créer un environnement virtuel dans `bin/` :

```bash
python3.8 -m venv bin
bin/pip install -r requirements.txt
```

## Lancement

```bash
bin/python main.py
```

## Commandes

| Touche | Action |
|---|---|
| Flèches / ZQSD | Déplacer le personnage |
| `U` | Annuler le dernier mouvement |
| `R` | Refaire |
| `Maj+R` / `F5` | Recommencer le niveau |
| `Échap` | Pause / retour au menu |
| `F11` | Plein écran |

## Règles du jeu

Poussez toutes les caisses sur les cibles (cases marquées). Le personnage ne peut pousser qu'une caisse à la fois et ne peut pas tirer. Le niveau est résolu quand toutes les cibles sont occupées.

## Modes de jeu

### Entraînement
Jeu libre, niveaux débloqués progressivement. Chaque niveau est noté de 1 à 3 étoiles selon le nombre de mouvements par rapport à la solution optimale.

### Tournoi
Enchaînement chronométré de tous les niveaux d'un pack. Chaque niveau est noté sur 2000 points (voir [Algorithme de score](#algorithme-de-score--mode-tournoi) ci-dessous). Le score total s'affiche à la fin.

## Panneau enseignant

Accessible depuis l'écran de connexion professeur (code PIN requis).

- **Gestion des élèves** — liste des élèves, consultation et rejeu de chaque tentative enregistrée, historique des tournois par élève avec détail niveau par niveau.
- **Stats classe tournoi** — sélectionner un pack pour afficher :
  - *Classement* : tous les élèves classés par meilleur score de tournoi
  - *Par niveau* : moyennes de la classe (score, nombre d'essais, temps) pour chaque niveau

## Packs de niveaux

| Pack | Description |
|---|---|
| Training | Niveaux d'initiation, toujours disponibles |
| Easy | Niveaux faciles |
| Original | Niveaux classiques Sokoban |
| Microban | Petits niveaux compacts |
| Sasquatch | Niveaux avancés |
| Saint-Luc | Pack spécifique, toujours disponible |

Les fichiers de niveaux (format XSB) se trouvent dans `levels/`. Le nombre optimal de mouvements est stocké en commentaire (`;optimal:N`) et utilisé pour les étoiles et le score de tournoi.

---

## Algorithme de score — Mode Tournoi

Chaque niveau complété rapporte jusqu'à **2000 points**, répartis en quatre composantes.

### 1. Efficacité des mouvements — jusqu'à 1000 pts

```
ratio   = min(1.0, optimal / mouvements)
points  = int(ratio * 1000)
```

- Solution optimale (mouvements == optimal) → **1000 pts**
- Deux fois l'optimal → **500 pts**
- Si le nombre optimal est inconnu, le score réel est utilisé à la place, accordant toujours **1000 pts**.

### 2. Pénalité de tentatives — jusqu'à 500 pts

```
points = max(0, 500 - (tentatives - 1) * 100)
```

| Tentatives | Points |
|---|---|
| 1 | 500 |
| 2 | 400 |
| 3 | 300 |
| 4 | 200 |
| 5 | 100 |
| 6+ | 0 |

Chaque relance du niveau coûte 100 pts. Le compteur est remis à 1 au passage au niveau suivant.

### 3. Bonus de rapidité — jusqu'à 500 pts

```
points = max(0, 500 - int(secondes))
```

- Résolu instantanément → **500 pts** (maximum théorique)
- Chaque seconde écoulée retire 1 pt
- Au-delà de 500 s → **0 pts**

### 4. Pénalité d'annulations — −1 pt par annulation

```
pénalité = annulations × 1
```

Chaque annulation (touche Undo) retire **1 point** du score total du niveau. Il n'y a pas de plafond.

### Score total

Les scores par niveau sont additionnés à la fin du tournoi :

```
total = somme des scores de chaque niveau
score_niveau = mouvements_pts + tentatives_pts + rapidité_pts − pénalité_annulations
(minimum 0)
```

Le maximum théorique est de **2000 × N pts** (N = nombre de niveaux du pack).

## Distribution Windows (construction de l'exécutable)

Le script `build/build_windows.sh` génère un exécutable Windows autonome via Wine + PyInstaller.
**Aucun Python n'est nécessaire sur le PC cible.**

### Pré-requis (sur la machine Linux/Ubuntu)

- `wine` : `sudo apt install wine`
- `python-3.8.20.exe` — installateur Python 3.8 pour Windows, à télécharger et placer à la racine du dépôt (ou passer le chemin en argument)

### Construction

```bash
bash build/build_windows.sh
# ou : bash build/build_windows.sh /chemin/vers/python-3.8.20.exe
```

Le script installe Python 3.8 sous Wine, puis `pygame-ce` et `pyinstaller`, et produit l'exécutable via `build/sokoban.spec`.

### Résultat

Le dossier `dist_win/sokoban/` contient l'application complète (exe + DLL + niveaux + assets).

### Installation sur le PC Windows cible

Copier **l'intégralité du dossier** `dist_win/sokoban/` sur le PC cible, puis lancer `sokoban.exe`.

> Les données de progression (`save.json`) et les fichiers élèves (`students/`) sont créés automatiquement à côté de l'exécutable au premier lancement — le dossier doit donc être accessible en écriture.

---

## Licence

Ce projet est distribué sous licence [GNU GPL v3](LICENSE).
