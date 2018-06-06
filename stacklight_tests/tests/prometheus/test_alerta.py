import pytest


@pytest.mark.smoke
def test_alerta_smoke(alerta_api):
    alerta_api.get_count()
