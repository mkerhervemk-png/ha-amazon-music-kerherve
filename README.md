# Amazon Music pour Home Assistant (non officiel)

Intégration personnalisée qui réutilise la session de **music.amazon.fr**.
Version 0.6.0 : entités, lecture, écriture et lancement sur Alexa. Procédure de test : voir `TESTING.md`.

> ⚠️ Non officielle. Amazon ne fournit pas d'API publique pour Amazon Music (la Web API est en bêta fermée).
> Cette intégration rejoue les requêtes internes du site. Elle peut cesser de fonctionner à chaque mise à jour du site, et son usage n'est pas prévu par les conditions d'Amazon.

## Entités
Regroupées sous l'appareil « Amazon Music », relues toutes les 30 minutes :
- `binary_sensor.amazon_music_connexion` : session valide ou non.
- `sensor.amazon_music_playlists`, `sensor.amazon_music_playlists_suivies` : nombre, liste en attribut `playlists`.
- `sensor.amazon_music_titres_aimes`, `sensor.amazon_music_dernier_titre_aime` (avec pochette).
- `select.amazon_music_playlist` : choix d'une playlist, identifiant en attribut `playlist_id`.
- `button.amazon_music_actualiser`.

## Services
Lecture (réponse obligatoire) :
- `get_track` : titre, artistes, album, pochette, durée, avis.
- `list_playlists` : playlists créées par le compte, toutes les pages.
- `list_followed_playlists` : playlists suivies, toutes les pages.
- `get_playlist_tracks` : titres d'une playlist avec artistes, pages suivies jusqu'à `limit`.
- `search` : suggestions rapides.
- `search_catalog` : recherche complète par type (`track`, `artist`, `album`, `playlist`).

Écriture (modifient le compte Amazon Music) :
- `create_playlist`, `delete_playlist` (suppression définitive).
- `add_track_to_playlist`, `remove_track_from_playlist`.
- `set_track_like` : `LIKE`, `NEUTRAL` ou `DISLIKE`.

Lecture sur enceinte :
- `play_on_alexa` : transmet une demande à Alexa Media Player (`media_player.play_media`, type `AMAZON_MUSIC`). Alexa cherche par nom : le résultat dépend de sa compréhension du titre.

## Session expirée
Quand Amazon refuse la session, Home Assistant affiche une demande de reconnexion : recoller la ligne `cookie`. On peut aussi le faire à tout moment par « Reconfigurer ».

## Ce qui n'est pas fait
- Connexion par identifiant et mot de passe (les cookies restent à copier).
- Albums et artistes de la bibliothèque, podcasts, file d'attente.
- Entité lecteur multimédia propre à l'intégration (l'état de lecture passe par Alexa Media Player).

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
