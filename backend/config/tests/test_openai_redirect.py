import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_admin_openai_api_key_redirect_superuser(client, django_user_model):
    u = django_user_model.objects.create_superuser("su", "su@example.com", "pass")
    client.force_login(u)
    url = reverse("admin-openai-api-key")
    res = client.get(url, follow=True)
    assert res.status_code == 200
    assert res.request["PATH_INFO"] == "/admin/ai/openaisettings/1/change/"


@pytest.mark.django_db
def test_admin_openai_api_key_redirects_staff_to_login(client, django_user_model):
    """Django 5.2 の user_passes_test は不合格時に常にログインへリダイレクトする。"""
    st = django_user_model.objects.create_user(
        "st", "st@example.com", "pass", is_staff=True, is_superuser=False
    )
    client.force_login(st)
    res = client.get(reverse("admin-openai-api-key"))
    assert res.status_code == 302
    assert "/app/login" in res["Location"]
