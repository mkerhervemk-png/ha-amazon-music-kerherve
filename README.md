# Amazon Music pour Home Assistant (non officiel)

Intégration personnalisée qui réutilise la session de **music.amazon.fr**.
Version 0.3.0 : lecture seule, cinq services (`get_track`, `list_playlists`, `get_playlist_tracks`, `search`). Procédure de test : voir `TESTING.md`.

> ⚠️ Non officielle. Amazon ne fournit pas d'API publique pour Amazon Music (la Web API est en bêta fermée).
> Cette intégration rejoue les requêtes internes du site. Elle peut cesser de fonctionner à chaque mise à jour du site, et son usage n'est pas prévu par les conditions d'Amazon.

## Ce qui est fait
- Saisie des cookies de session dans l'assistant de configuration.
- Test de la session (lecture des métadonnées d'un titre de contrôle).
- Service `amazon_music.get_track` : titre, artistes, album, pochette.
- Service `amazon_music.list_playlists` : playlists créées par le compte (première page).
- Service `amazon_music.get_playlist_tracks` : titres d'une playlist (première page).
- Service `amazon_music.search` : suggestions de recherche (artistes, playlists, titres). Ce n'est pas la page de résultats complète.

## Ce qui n'est pas fait (à venir, sur validation)
- Bibliothèque suivie (playlists suivies), pagination au-delà de la première page, résultats de recherche complets.
- Toute écriture (créer une playlist, aimer un titre, ajouter un titre).
- Lecture sur Echo / Fire TV : prévue via Alexa Media Player, pas via cette intégration.
- Écriture (créer une playlist, aimer un titre) : désactivée.

## Installation
1. Copier `custom_components/amazon_music` dans `/config/custom_components/`.
2. Redémarrer Home Assistant.
3. Paramètres → Appareils et services → Ajouter une intégration → « Amazon Music (non officiel) ».

## Récupérer les cookies
1. Connectez-vous sur music.amazon.fr dans Chrome.
2. F12 → Application (ou Stockage) → Cookies → `https://music.amazon.fr`.
3. Copiez les valeurs de `session-token` et `session-id`. `csrf` est optionnel.

Ces cookies donnent accès à votre compte. Ne les partagez pas, ne les commitez jamais. Ils sont stockés dans la configuration de Home Assistant (`.storage`), lisible par les administrateurs de l'instance.

## Points non vérifiés
- Extraction automatique du jeton CSRF depuis la page (`api.py`, `async_refresh_csrf`) : non confirmée sur une réponse réelle. Si elle échoue, renseignez `csrf` manuellement.
- Requêtes GraphQL écrites à la main (`const.py`) : vérifiées le 13/11/2026 avec une session de test. Le schéma peut changer lors d'une mise à jour du site.

## Dépannage
- « Cookies refusés » : reconnectez-vous sur le site et recopiez les cookies.
- Erreur GraphQL : le schéma du site a probablement changé ; les requêtes sont dans `const.py`.
