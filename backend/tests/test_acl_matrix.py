"""Matrice dei permessi (task 1.8): ogni ruolo per ogni azione principale, inclusi 403 e 404.

Convenzioni sugli esiti attesi:
- "ok": l'accesso e' concesso (le richieste hanno corpo volutamente non valido, quindi
  l'esito e' 422/400 e non parte nessuna chiamata AI: conta che non sia 401, 403 o 404);
- 403: il progetto esiste per te ma l'azione non e' consentita al tuo ruolo;
- 404: per te il progetto non esiste, senza rivelare che esiste.
"""
import uuid

import pytest

from app.core.auth import get_current_user
from app.main import app

OWNER = "test-user"
ACTORS = {
    "owner": ("test-user", "owner@example.com", []),
    "editor": ("u-editor", "editor@example.com", []),
    "viewer": ("u-viewer", "viewer@example.com", []),
    "stranger": ("u-stranger", "stranger@example.com", []),
    "link": ("u-link", "link@example.com", []),
    "admin": ("u-admin", "admin@example.com", ["aidb-admin"]),
}


def as_user(sub, email=None, roles=None):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email, "roles": roles or [], "email_verified": True}


# azione -> (metodo, percorso, tipo di corpo)
BAD = {"json": []}  # corpo non valido: 422 se l'accesso e' concesso, senza chiamare il modello
ACTIONS = {
    "vedere_progetto": ("GET", "/api/projects/{pid}", {}),
    "vedere_schema": ("GET", "/api/projects/{pid}/schema", {}),
    "vedere_documenti": ("GET", "/api/projects/{pid}/documents", {}),
    "caricare_documento": ("POST", "/api/projects/{pid}/documents", {}),
    "modificare_schema": ("PUT", "/api/projects/{pid}/schema", BAD),
    "generare": ("POST", "/api/projects/{pid}/generate", BAD),
    "popolare": ("POST", "/api/projects/{pid}/populate", BAD),
    "query_lettura": ("POST", "/api/projects/{pid}/execute-query", BAD),
    "domanda_in_linguaggio_naturale": ("POST", "/api/projects/{pid}/query", BAD),
    "esportare": ("GET", "/api/projects/{pid}/export", {}),
    "vedere_condivisione": ("GET", "/api/projects/{pid}/sharing", {}),
    "invitare": ("POST", "/api/projects/{pid}/invites", {"json": {"email": "x@example.com", "role": "viewer"}}),
    "creare_link": ("POST", "/api/projects/{pid}/links", {}),
    "cancellare_progetto": ("DELETE", "/api/projects/{pid}", {}),
    "uso_e_costi": ("GET", "/api/admin/usage?group=user", {}),
    "bloccare_utenti": ("PUT", "/api/admin/users/{owner}", {"json": {"blocked": True}}),
}

# Esiti per ruolo, nell'ordine owner, editor, viewer, stranger, link, admin.
O, E, V, S, L, A = "owner", "editor", "viewer", "stranger", "link", "admin"
EXPECTED = {
    "vedere_progetto": (200, 200, 200, 404, 404, 404),
    "vedere_schema": (200, 200, 200, 404, 404, 404),
    "vedere_documenti": (200, 200, 200, 404, 404, 404),
    "caricare_documento": ("ok", "ok", 403, 404, 404, 404),
    "modificare_schema": ("ok", "ok", 403, 404, 404, 404),
    "generare": ("ok", "ok", 403, 404, 404, 404),
    "popolare": ("ok", "ok", 403, 404, 404, 404),
    "query_lettura": ("ok", "ok", "ok", 404, 404, 404),
    "domanda_in_linguaggio_naturale": ("ok", "ok", "ok", 404, 404, 404),
    "esportare": ("ok", "ok", "ok", 404, 404, 404),
    "vedere_condivisione": (200, 403, 403, 404, 404, 404),
    "invitare": (200, 403, 403, 404, 404, 404),
    "creare_link": (200, 403, 403, 404, 404, 404),
    "cancellare_progetto": (200, 403, 403, 404, 404, 404),
    "uso_e_costi": (403, 403, 403, 403, 403, 200),
    "bloccare_utenti": (403, 403, 403, 403, 403, 200),
}
ROLES = (O, E, V, S, L, A)
CELLS = [(action, role, EXPECTED[action][i]) for action in ACTIONS for i, role in enumerate(ROLES)]


@pytest.fixture(autouse=True)
def no_keycloak_at_startup(monkeypatch):
    """Evita il tentativo di rete verso Keycloak all'avvio dell'app: renderebbe lenta ogni cella."""
    async def noop():
        return False
    monkeypatch.setattr("app.main.setup_keycloak_realm", noop)


@pytest.fixture()
def world(client, project):
    """Un progetto con proprietario, editor e lettore gia' registrati e un link pubblico attivo."""
    c, _ = client
    pid = project["id"]
    for name in (E, V, S, L, A):
        sub, email, roles = ACTORS[name]
        as_user(sub, email, roles)
        c.get("/api/me")
    as_user(*ACTORS[O])
    c.get("/api/me")
    for name, role in ((E, "editor"), (V, "viewer")):
        assert c.post(f"/api/projects/{pid}/invites", json={"email": ACTORS[name][1], "role": role}).status_code == 200
    token = c.post(f"/api/projects/{pid}/links").json()["token"]
    return c, pid, token


def call(c, pid, action):
    method, path, kwargs = ACTIONS[action]
    return c.request(method, path.format(pid=pid, owner=OWNER), **kwargs)


@pytest.mark.parametrize("action,role,expected", CELLS, ids=[f"{a}-{r}" for a, r, _ in CELLS])
def test_acl_cell(world, action, role, expected):
    c, pid, _ = world
    as_user(*ACTORS[role])
    res = call(c, pid, action)
    if expected == "ok":
        assert res.status_code not in (401, 403, 404), (res.status_code, res.text)
    else:
        assert res.status_code == expected, (res.status_code, res.text)


@pytest.mark.parametrize("role", ROLES)
def test_public_link_view_is_open_to_everyone_but_read_only(world, role):
    c, pid, token = world
    as_user(*ACTORS[role])
    data = c.get(f"/api/shared/{token}").json()
    assert data["read_only"] is True and "token" not in str(data)


def test_invalid_link_is_404(world):
    c, _, _ = world
    as_user(*ACTORS[L])
    assert c.get("/api/shared/token-inesistente").status_code == 404


def test_link_does_not_unlock_project_endpoints(world):
    c, pid, token = world
    as_user(*ACTORS[L])
    assert c.get(f"/api/shared/{token}").status_code == 200
    for action in ("vedere_progetto", "vedere_schema", "esportare", "query_lettura"):
        assert call(c, pid, action).status_code == 404


@pytest.mark.parametrize("action", [a for a in ACTIONS if a not in ("uso_e_costi", "bloccare_utenti")])
def test_blocked_user_gets_403_everywhere(world, action):
    c, pid, _ = world
    as_user(*ACTORS[A])
    assert c.put(f"/api/admin/users/{ACTORS[E][0]}", json={"blocked": True}).status_code == 200
    as_user(*ACTORS[E])
    res = call(c, pid, action)
    assert res.status_code == 403 and "sospeso" in res.json()["detail"]


@pytest.mark.parametrize("role", (S, L, A))
def test_404_is_identical_for_existing_and_missing_projects(world, role):
    c, pid, _ = world
    as_user(*ACTORS[role])
    missing = str(uuid.uuid4())
    for action in ("vedere_progetto", "vedere_schema", "cancellare_progetto"):
        real, fake = call(c, pid, action), call(c, missing, action)
        assert real.status_code == fake.status_code == 404
        assert real.json() == fake.json()


def test_admin_can_read_admin_endpoints_but_not_project_content(world):
    c, pid, _ = world
    as_user(*ACTORS[A])
    assert c.get("/api/admin/overview").status_code == 200
    assert c.get(f"/api/projects/{pid}/schema").status_code == 404
