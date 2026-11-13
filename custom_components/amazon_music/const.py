"""Constantes de l'intégration Amazon Music."""

DOMAIN = "amazon_music"

CONF_SESSION_TOKEN = "session_token"
CONF_SESSION_ID = "session_id"
CONF_CSRF = "csrf"
CONF_DEVICE_ID = "device_id"

GQL_URL = "https://gql.music.amazon.fr/"
WEB_URL = "https://music.amazon.fr/"

# Identifiant public de l'application web (visible dans les requêtes du navigateur).
API_KEY = "amzn1.application.4ff5579ca2e3407aba989a1f5dbdaf69"
TERRITORY = "FR"

# Opérations GraphQL persistées (hash SHA-256 par release du site).
# Ces hashes changent à chaque mise à jour d'Amazon Music : ils doivent
# être revérifiés si une requête répond avec une erreur "PersistedQueryNotFound".
OP_MEDIA_SESSION_METADATA = "MediaSessionMeatadata"
HASH_MEDIA_SESSION_METADATA = (
    "cbeb58d74b06856d07d15de6d286c66de25fbdcb950bd464f27c0a76abeabc19"
)

SERVICE_GET_TRACK = "get_track"
