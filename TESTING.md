# Procédure de test dans Home Assistant

Objectif : vérifier les 5 services en lecture seule, sur ton instance, avec ta session.
Aucune écriture (playlist, « j'aime ») n'est présente dans cette version.

## 0. Sauvegarde
Paramètres → Système → Sauvegardes → « Sauvegarder maintenant ».

## 1. Copier le composant
Copier le dossier `custom_components/amazon_music` du dépôt vers `/config/custom_components/amazon_music` (par exemple via l'add-on Samba ou File editor).
Vérifier que le dossier contient `__init__.py`, `api.py`, `config_flow.py`, `const.py`, `manifest.json`, `services.yaml`, `strings.json`.

## 2. Redémarrer Home Assistant
Paramètres → Système → Redémarrer. Ne pas le faire pendant une coupure ou une automatisation sensible.

## 3. Ajouter l'intégration
Paramètres → Appareils et services → Ajouter une intégration → « Amazon Music (non officiel) ».
Coller la ligne `cookie` complète (récupération décrite dans le README, section « Récupérer les cookies »).

Résultats attendus :
- L'intégration se crée sans erreur.
- Si « Cookies ou en-têtes CSRF refusés » : recopiez les deux cookies et les trois en-têtes depuis une même requête gql récente.
- Si « Connexion impossible » : vérifier l'accès réseau de HA vers `gql.music.amazon.fr`.

## 4. Tester les services
Outils de développement → Actions. Activer « Afficher la réponse ». Pour chaque service ci-dessous, cliquer sur « Exécuter l'action ».

| Service | Données | Attendu |
|---|---|---|
| `amazon_music.get_track` | `track_id: B0GWPYXQHB` | `title: New Religion`, album et pochette |
| `amazon_music.list_playlists` | `limit: 10` | liste de playlists, dont « Mes Likes » |
| `amazon_music.get_playlist_tracks` | `playlist_id: b7048fc052e14b6ebb6d14198e191c62`, `limit: 5` | 5 titres de « Mes Likes » |
| `amazon_music.search` | `query: bach` | artistes, playlists et titres |

Les services ne modifient rien : ils se lisent seulement.

## 5. Vérifier les journaux
Paramètres → Système → Journaux. Filtrer sur `amazon_music`. Aucune erreur attendue après les tests.

## 6. En cas de problème
- « Erreur GraphQL » : le schéma du site a probablement changé. Ne pas insister, noter le message exact et le renvoyer.
- `invalid_auth` : cookies incomplets ou session Amazon expirée, recoller la ligne `cookie`.

## 7. Retour arrière
1. Paramètres → Appareils et services → Amazon Music → Supprimer.
2. Supprimer le dossier `/config/custom_components/amazon_music`.
3. Redémarrer Home Assistant.

## Sécurité
- Ne jamais mettre les cookies dans une automatisation, un script ou un fichier YAML. Ils restent dans la configuration de l'intégration.
- Ne pas partager les captures d'écran de la configuration de l'intégration.
