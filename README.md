# Amazon Music pour Home Assistant (non officiel)

Intégration personnalisée qui réutilise la session de **music.amazon.fr**.
Version 0.3.0 : lecture seule, cinq services (`get_track`, `list_playlists`, `get_playlist_tracks`, `search`). Procédure de test : voir `TESTING.md`.

> ⚠️ Non officielle. Amazon ne fournit pas d'API publique pour Amazon Music (la Web API est en bêta fermée).
> Cette intégration rejoue les requêtes internes du site. Elle peut cesser de fonctionner à chaque mise à jour du site, et son usage n'est pas prévu par les conditions d'Amazon.

## Ce qui est fait
- Saisie des cookies de session dans l'assistant de configuration.
- Test de la session (compte reconnu sur `config.json`, puis lecture des playlists).
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
Depuis la version 0.4.0, un seul champ est demandé : la ligne `cookie` de la session.

1. Ouvrir `music.amazon.fr` dans le navigateur, connecté au compte.
2. F12, onglet **Réseau**, recharger la page.
3. Cliquer sur la requête `config.json` (ou une requête `gql`).
4. Dans **En-têtes de requête**, copier toute la valeur de la ligne `cookie`.
5. La coller dans le champ de l'intégration.

Les jetons CSRF, l'appareil et la session sont lus automatiquement sur `config.json` et renouvelés par le composant.

## Points non vérifiés
- Liste exacte des cookies exigés par Amazon : non déterminée, d'où la ligne complète.
- Durée de vie de la session Amazon : inconnue. À l'expiration, recoller les cookies.
- Requêtes GraphQL écrites à la main (`const.py`) : vérifiées le 13/11/2026. Le schéma peut changer lors d'une mise à jour du site.

## Dépannage
- « Cookies refusés » : reconnectez-vous sur le site et recopiez les cookies.
- Erreur GraphQL : le schéma du site a probablement changé ; les requêtes sont dans `const.py`.
