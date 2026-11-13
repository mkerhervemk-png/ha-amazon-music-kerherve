"""Constantes de l'intégration Amazon Music."""

DOMAIN = "amazon_music"

CONF_COOKIES = "cookies"

GQL_URL = "https://gql.music.amazon.fr/"
WEB_URL = "https://music.amazon.fr/"
# Renvoie (en POST) les jetons CSRF, l'appareil, la session et le compte.
CONFIG_URL = "https://music.amazon.fr/config.json"
# Durée de réutilisation des jetons CSRF avant de les redemander.
CSRF_MAX_AGE = 1800

# Identifiant public de l'application web (visible dans les requêtes du navigateur).
API_KEY = "amzn1.application.4ff5579ca2e3407aba989a1f5dbdaf69"
TERRITORY = "FR"

# Requêtes GraphQL écrites à la main (courtes). Le serveur les accepte en texte
# complet, sans hash persisté : elles ne dépendent donc pas des hashes du site.
# Vérifié le 13/11/2026 avec la session de test.
QUERY_TRACK = """
query Track($id: String!) {
  track(id: $id) {
    id
    title
    album { title images { url } }
    contributingArtists { edges { node { name } } }
  }
}
"""

QUERY_USER_PLAYLISTS = """
query UserPlaylists($firstLimit: Float!, $afterCursor: String) {
  user {
    id
    playlists(limit: $firstLimit, cursor: $afterCursor) {
      edges { node { id title trackCount } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

QUERY_PLAYLIST_TRACKS = """
query PlaylistTracks($id: String!, $limit: Float!) {
  playlist(id: $id) {
    id
    title
    trackCount
    tracks(limit: $limit) {
      edges { node { id title } }
    }
  }
}
"""

# Renvoie des suggestions (artistes, playlists, titres) : c'est la recherche
# disponible sur ce point d'entrée, pas la page de résultats complète.
QUERY_SEARCH = """
query GetSearchSuggestions($query: String!) {
  searchSuggestions(query: $query) {
    id
    suggestedEntities {
      edges {
        node {
          __typename
          ... on Track { id title }
          ... on Artist { id name }
          ... on Album { id title }
          ... on Playlist { id title }
        }
      }
    }
  }
}
"""

SERVICE_GET_TRACK = "get_track"
SERVICE_LIST_PLAYLISTS = "list_playlists"
SERVICE_GET_PLAYLIST_TRACKS = "get_playlist_tracks"
SERVICE_SEARCH = "search"
