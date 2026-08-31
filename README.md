# Sorties 77 — scraper

Récupère automatiquement les programmations culturelles de plusieurs salles
de Seine-et-Marne / Marne-la-Vallée et les fusionne dans un seul fichier
`output/events.json`, que l'appli `sorties77.html` peut ensuite charger.

## Installation

```bash
pip install -r requirements.txt
```

(Python 3.9 ou plus récent recommandé.)

## Utilisation

```bash
python run_all.py
```

Ça affiche le nombre d'événements trouvés par source, puis écrit
`output/events.json`.

## Important — à savoir avant de lancer

Ces scrapers ont été écrits **sans pouvoir tester l'accès réel aux sites**
(mon environnement de développement n'a pas accès à internet en dehors
d'une liste de domaines techniques). Ils reposent sur des hypothèses
raisonnables concernant la structure HTML de chaque site, mais **il est très
probable qu'il faille les ajuster** une fois lancés en conditions réelles :

1. Lance `python run_all.py`
2. Si un scraper renvoie 0 résultat, ouvre la page concernée dans ton
   navigateur, fais un clic droit -> **Inspecter**, et regarde comment les
   dates et titres sont structurés (quelles balises, quelles classes CSS)
3. Ajuste les sélecteurs dans le fichier `scrapers/xxx.py` correspondant

Je suis dispo pour t'aider à corriger un scraper si tu me montres un extrait
du HTML réel de la page (Ctrl+U ou "Afficher le code source", copier-coller
la portion qui contient un événement).

## Sources couvertes

| Fichier | Salle | Fiabilité attendue |
|---|---|---|
| `scrapers/millesime.py` | Le Millésime, Montévrain | Bonne — page HTML simple, programme jusqu'à mai 2027 |
| `scrapers/lescuizines.py` | Les Cuizines, Chelles | Moyenne — dépend du plugin d'agenda utilisé |
| `scrapers/file7.py` | File7, Magny-le-Hongre | Moyenne |
| `scrapers/ferme_du_buisson.py` | Ferme du Buisson, Noisiel | Moyenne — filtre le cinéma, à vérifier |
| `scrapers/apidae_fiche.py` | Auditorium Jean-Cocteau, Espace Marc Brinon | Bonne — pages institutionnelles stables |

## Sources volontairement absentes

- **La Courée (Collégien)** et **Espace Lino-Ventura (Torcy)** : pas encore
  écrits, mais suivent le même modèle que `lescuizines.py` — je peux les
  ajouter facilement.
- **Ferme des Communes (Serris)**, **Le Millésime version Fnac** : passent
  par Fnac Spectacles, qui bloque explicitement le scraping via son
  `robots.txt`. Ne pas contourner ça — c'est une limite légale, pas
  seulement technique.
- **La Sucrerie / Théâtre municipal (Coulommiers)** : la plaquette est sur
  Calameo, qui affiche son contenu en SVG généré par JavaScript — très
  difficile à scraper proprement. Mieux vaut mettre ces dates à la main une
  fois par saison à partir du PDF, plutôt que de scraper.
- **3 Brasseurs (Chanteloup-en-Brie)** : aucune source structurée n'existe.

## Automatiser l'exécution

### Sur Windows (Planificateur de tâches)
1. Ouvre le "Planificateur de tâches"
2. Crée une tâche qui exécute `python run_all.py` tous les jours, par
   exemple à 6h du matin
3. Renseigne le "dossier de démarrage" = le dossier de ce projet

### Sur Mac/Linux (cron)
```bash
crontab -e
# ajoute la ligne suivante pour un run quotidien à 6h :
0 6 * * * cd /chemin/vers/sorties77-scraper && /usr/bin/python3 run_all.py
```

### Connecter le résultat à l'appli
Une fois `output/events.json` généré, remplace dans `sorties77.html` le
tableau `const events = [...]` codé en dur par un chargement du fichier :

```js
fetch('events.json')
  .then(r => r.json())
  .then(data => { events.length = 0; events.push(...data); render(); buildCalendar(); });
```

(Il faudra alors servir les deux fichiers depuis un petit serveur local —
`python -m http.server` suffit pour un usage perso — car les navigateurs
bloquent `fetch()` sur un fichier ouvert directement en `file://`.)
