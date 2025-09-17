import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_logout_via_post(client, django_user_model):
    user = django_user_model.objects.create_user(username="user", password="pass")
    client.force_login(user)
    response = client.post(reverse("logout"))
    assert response.status_code == 302
    assert response.url == reverse("core:login")
    assert "_auth_user_id" not in client.session

