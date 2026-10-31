from core.config import settings

ORIGEM = settings.cors_origins[0]


def test_preflight_da_origem_do_frontend_e_aceito(client):
    r = client.options(
        "/membros",
        headers={
            "Origin": ORIGEM,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGEM


def test_origem_desconhecida_nao_recebe_cabecalho_cors(client):
    r = client.get("/health", headers={"Origin": "https://malicioso.example"})
    assert "access-control-allow-origin" not in r.headers


def test_401_do_middleware_jwt_tambem_leva_cors(client):
    r = client.get("/membros", headers={"Origin": ORIGEM})
    assert r.status_code == 401
    assert r.headers["access-control-allow-origin"] == ORIGEM
