# Procédure de test dans Home Assistant

Objectif : vérifier les services (voir README), sur ton instance, avec ta session.

Cette version contient des services de **lecture** et des services de **modification** du compte Amazon. Ils sont séparés ci-dessous : la partie 4 (lecture seule) est la procédure par défaut. Les parties 5 et 6 (écritures) sont facultatives.

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

## 4. Tester les services de lecture (procédure par défaut)
Outils de développement → Actions. Activer « Afficher la réponse ». Pour chaque service ci-dessous, cliquer sur « Exécuter l'action ».

| Service | Données | Attendu |
|---|---|---|
| `amazon_music.get_track` | `track_id: B0GWPYXQHB` | `title: New Religion`, album et pochette |
| `amazon_music.list_playlists` | `limit: 10` | liste de playlists, dont « Mes Likes » |
| `amazon_music.get_playlist_tracks` | `playlist_id: b7048fc052e14b6ebb6d14198e191c62`, `limit: 5` | 5 titres de « Mes Likes » |
| `amazon_music.search` | `query: bach` | artistes, playlists et titres |

Ces services ne modifient pas le compte. Les services `list_followed_playlists` et `search_catalog` sont aussi en lecture seule.

## 5. Tester les services d'écriture (facultatif)
Ne lancer cette partie qu'avec une playlist de test créée pour l'occasion, par exemple « TEST ADRIA ». Ne jamais utiliser « Mes Likes » ni une playlist personnelle.

| Service | Effet sur le compte | Réversibilité |
|---|---|---|
| `amazon_music.create_playlist` | crée une playlist | réversible par `delete_playlist` |
| `amazon_music.add_track_to_playlist` | ajoute un titre à une playlist | réversible par `remove_track_from_playlist` |
| `amazon_music.remove_track_from_playlist` | retire un titre d'une playlist | réversible par `add_track_to_playlist` |
| `amazon_music.set_track_like` | change l'avis sur un titre (LIKE, NEUTRAL, DISLIKE) | réversible en remettant l'avis précédent |
| `amazon_music.delete_playlist` | supprime une playlist | **définitive** (voir partie 6) |

Déroulé conseillé : créer la playlist de test, y ajouter un titre, le retirer, changer l'avis d'un titre de test puis le remettre comme avant. Vérifier après chaque action que le capteur ou la liste est mis à jour.

Les nouveaux champs ne sont pas obligatoires dans les services existants : les scripts et automatisations actuels continuent de fonctionner.

## 6. Tester la suppression de playlist (facultatif, définitif)
`amazon_music.delete_playlist` ne fait pas partie des tests ordinaires. À n'utiliser que sur la playlist « TEST ADRIA ». La suppression est définitive : aucune restauration n'est possible depuis Home Assistant.

## 7. Vérifier les journaux
Paramètres → Système → Journaux. Filtrer sur `amazon_music`. Aucune erreur attendue après les tests.

## 8. En cas de problème
- « Erreur GraphQL » : le schéma du site a probablement changé. Ne pas insister, noter le message exact et le renvoyer.
- `invalid_auth` : cookies incomplets ou session Amazon expirée, recoller la ligne `cookie`. Une erreur d'authentification déclenche le parcours de réauthentification de Home Assistant.

## 9. Retour arrière
1. Paramètres → Appareils et services → Amazon Music → Supprimer.
2. Supprimer le dossier `/config/custom_components/amazon_music`.
3. Redémarrer Home Assistant.

## Sécurité
- Ne jamais mettre les cookies dans une automatisation, un script ou un fichier YAML. Ils restent dans la configuration de l'intégration.
- Ne pas partager les captures d'écran de la configuration de l'intégration.
