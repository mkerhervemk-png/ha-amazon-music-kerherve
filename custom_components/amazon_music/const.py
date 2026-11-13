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
# complet, sans hash persisté. Vérifiées le 13/11/2026 dans une session réelle.
# Pagination : le curseur à renvoyer est pageInfo.token (endCursor est vide).
PAGE_SIZE = 100

QUERY_TRACK = """
query Track($id: String!) {
  track(id: $id) {
    id
    title
    duration
    likesContext { state }
    album { title images { url } }
    contributingArtists { edges { node { name } } }
  }
}
"""

QUERY_USER_PLAYLISTS = """
query UserPlaylists($limit: Float!, $cursor: String) {
  user {
    id
    playlists(limit: $limit, cursor: $cursor, sortBy: "LAST_MODIFIED_DATE") {
      edges { node { id title trackCount } }
      pageInfo { hasNextPage token }
    }
  }
}
"""

QUERY_FOLLOWED_PLAYLISTS = """
query FollowedPlaylists($limit: Float, $cursor: String) {
  user {
    id
    followedPlaylists(limit: $limit, cursor: $cursor) {
      edges { node { id title trackCount } }
      pageInfo { hasNextPage token }
    }
  }
}
"""

QUERY_PLAYLIST_TRACKS = """
query PlaylistTracks($id: String!, $limit: Float!, $cursor: String) {
  playlist(id: $id) {
    id
    title
    trackCount
    tracks(limit: $limit, cursor: $cursor) {
      edges {
        cursor
        node { id title contributingArtists { edges { node { name } } } }
      }
      pageInfo { hasNextPage token }
    }
  }
}
"""

# Suggestions rapides (quelques résultats, tous types mélangés).
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

# Recherche complète dans le catalogue, par type.
QUERY_SEARCH_CATALOG = """
query SpecSearch($searchText: String!, $specifications: [SearchSpecification]) {
  specificationSearch(
    specificationSearchInput: { searchText: $searchText, specifications: $specifications }
  ) {
    id
    result {
      label
      edges {
        node {
          __typename
          ... on Track { id title contributingArtists { edges { node { name } } } }
          ... on Artist { id name }
          ... on Album { id title }
          ... on Playlist { id title }
        }
      }
    }
  }
}
"""

SEARCH_TYPES = ["track", "artist", "album", "playlist"]

# --- Écritures (modifient le compte Amazon Music) ---
MUTATION_CREATE_PLAYLIST = """
mutation CreatePlaylist($title: String!, $description: String, $trackAsins: [String]) {
  createPlaylist(title: $title, description: $description, trackAsins: $trackAsins) {
    id
    title
  }
}
"""

MUTATION_DELETE_PLAYLIST = """
mutation deletePlaylist($id: String!) {
  deletePlaylist(id: $id) { id isDeleted }
}
"""

MUTATION_ADD_TRACK = """
mutation addTrackToPlaylist($id: String!, $trackId: String!, $rejectDuplicateTracks: Boolean) {
  appendTracks(playlistId: $id, trackIds: [$trackId], rejectDuplicateTracks: $rejectDuplicateTracks) {
    id
    trackCount
  }
}
"""

MUTATION_REMOVE_TRACK = """
mutation removeTrackFromPlaylist($id: String!, $cursor: String!) {
  removeTracks(playlistId: $id, entryIds: [$cursor]) {
    id
    trackCount
  }
}
"""

MUTATION_SET_LIKE = """
mutation likeTrack($likeState: String, $trackId: String!) {
  setTrackLikeState(likeState: $likeState, trackId: $trackId) {
    track { id likesContext { state } }
  }
}
"""

LIKE_STATES = ["LIKE", "NEUTRAL", "NONE", "DISLIKE"]

SERVICE_GET_TRACK = "get_track"
SERVICE_LIST_PLAYLISTS = "list_playlists"
SERVICE_LIST_FOLLOWED_PLAYLISTS = "list_followed_playlists"
SERVICE_GET_PLAYLIST_TRACKS = "get_playlist_tracks"
SERVICE_SEARCH = "search"
SERVICE_SEARCH_CATALOG = "search_catalog"
SERVICE_CREATE_PLAYLIST = "create_playlist"
SERVICE_DELETE_PLAYLIST = "delete_playlist"
SERVICE_ADD_TRACK = "add_track_to_playlist"
SERVICE_REMOVE_TRACK = "remove_track_from_playlist"
SERVICE_SET_TRACK_LIKE = "set_track_like"
SERVICE_PLAY_ON_ALEXA = "play_on_alexa"
