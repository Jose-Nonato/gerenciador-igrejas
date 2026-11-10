import pytest

from core import armazenamento
from models.enums import PerfilUsuario

# Cabeçalhos mínimos: o backend só confere a assinatura do arquivo
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16
GIF = b"GIF89a" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _pasta_propria(tmp_path, monkeypatch):
    """O banco é limpo entre os testes, os arquivos não: cada teste usa uma pasta nova."""
    monkeypatch.setattr("core.config.settings.UPLOAD_DIR", str(tmp_path))


@pytest.fixture
def igreja(criar_igreja):
    return criar_igreja("Igreja A")


@pytest.fixture
def admin(criar_usuario, igreja):
    return criar_usuario(igreja, "admin@a.org", perfil=PerfilUsuario.ADMIN)


@pytest.fixture
def h(auth, admin):
    return auth(admin)


@pytest.fixture
def usuario(auth, criar_usuario, igreja):
    return auth(criar_usuario(igreja, "leitor@a.org", perfil=PerfilUsuario.USUARIO))


@pytest.fixture
def comunicado(client, h):
    r = client.post(
        "/comunicados", headers=h,
        json={"titulo": "Culto", "corpo": "Domingo.", "categoria": "aviso", "publico": "igreja"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def enviar(client, headers, comunicado_id, dados, nome="foto.png", tipo="image/png"):
    return client.put(
        f"/comunicados/{comunicado_id}/imagem", headers=headers, files={"arquivo": (nome, dados, tipo)}
    )


def test_sem_imagem_por_padrao(client, h, comunicado):
    assert comunicado["tem_imagem"] is False
    assert client.get(f"/comunicados/{comunicado['id']}/imagem", headers=h).status_code == 404


@pytest.mark.parametrize(
    "dados, tipo",
    [(PNG, "image/png"), (JPG, "image/jpeg"), (WEBP, "image/webp"), (GIF, "image/gif")],
)
def test_envia_e_baixa_a_imagem(client, h, comunicado, dados, tipo):
    r = enviar(client, h, comunicado["id"], dados)
    assert r.status_code == 200, r.text
    assert r.json()["tem_imagem"] is True

    r = client.get(f"/comunicados/{comunicado['id']}/imagem", headers=h)
    assert (r.status_code, r.headers["content-type"], r.content) == (200, tipo, dados)
    assert client.get(f"/comunicados/{comunicado['id']}", headers=h).json()["tem_imagem"] is True


def test_tipo_vem_do_conteudo_e_nao_do_nome(client, h, comunicado):
    # arquivo de texto disfarçado de imagem
    r = enviar(client, h, comunicado["id"], b"<script>alert(1)</script>", nome="x.png", tipo="image/png")
    assert r.status_code == 400
    assert "Formato" in r.json()["detail"]
    # e uma imagem real com nome e tipo errados é aceita pelo que ela é
    r = enviar(client, h, comunicado["id"], JPG, nome="x.txt", tipo="text/plain")
    assert r.status_code == 200
    assert client.get(f"/comunicados/{comunicado['id']}/imagem", headers=h).headers["content-type"] == "image/jpeg"


def test_recusa_arquivo_vazio_e_grande_demais(client, h, comunicado, monkeypatch):
    assert enviar(client, h, comunicado["id"], b"").status_code == 400
    monkeypatch.setattr("core.config.settings.MAX_IMAGEM_MB", 1)
    r = enviar(client, h, comunicado["id"], PNG + b"\x00" * (1024 * 1024))
    assert r.status_code == 400
    assert "1 MB" in r.json()["detail"]


def test_trocar_apaga_o_arquivo_antigo(client, h, comunicado):
    enviar(client, h, comunicado["id"], PNG)
    assert len(list(armazenamento.pasta().iterdir())) == 1
    enviar(client, h, comunicado["id"], JPG)
    arquivos = list(armazenamento.pasta().iterdir())
    assert len(arquivos) == 1 and arquivos[0].suffix == ".jpg"


def test_remover_imagem(client, h, comunicado):
    enviar(client, h, comunicado["id"], PNG)
    r = client.delete(f"/comunicados/{comunicado['id']}/imagem", headers=h)
    assert (r.status_code, r.json()["tem_imagem"]) == (200, False)
    assert list(armazenamento.pasta().iterdir()) == []
    assert client.delete(f"/comunicados/{comunicado['id']}/imagem", headers=h).status_code == 404


def test_leitor_ve_a_imagem_so_se_publicado(client, h, usuario, comunicado):
    enviar(client, h, comunicado["id"], PNG)
    url = f"/comunicados/{comunicado['id']}/imagem"
    # rascunho: some para quem só lê
    assert client.get(url, headers=usuario).status_code == 404
    client.post(f"/comunicados/{comunicado['id']}/publicar", headers=h, json={})
    assert client.get(url, headers=usuario).status_code == 200
    mural = client.get("/comunicados", headers=usuario).json()["items"]
    assert mural[0]["tem_imagem"] is True


def test_leitor_nao_envia_nem_remove_imagem(client, h, usuario, comunicado):
    client.post(f"/comunicados/{comunicado['id']}/publicar", headers=h, json={})
    assert enviar(client, usuario, comunicado["id"], PNG).status_code == 403
    enviar(client, h, comunicado["id"], PNG)
    assert client.delete(f"/comunicados/{comunicado['id']}/imagem", headers=usuario).status_code == 403


def test_imagem_exige_autenticacao(client, h, comunicado):
    enviar(client, h, comunicado["id"], PNG)
    assert client.get(f"/comunicados/{comunicado['id']}/imagem").status_code == 401


def test_imagem_de_outra_igreja_nao_aparece(client, h, comunicado, auth, criar_igreja, criar_usuario):
    enviar(client, h, comunicado["id"], PNG)
    outra = criar_igreja("Igreja B")
    hb = auth(criar_usuario(outra, "admin@b.org", perfil=PerfilUsuario.ADMIN))
    assert client.get(f"/comunicados/{comunicado['id']}/imagem", headers=hb).status_code == 404
    assert enviar(client, hb, comunicado["id"], JPG).status_code == 404
