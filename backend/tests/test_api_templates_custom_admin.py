from app.models.user import Role

from tests.conftest import auth_headers, make_disk_layout, make_organization, make_user


def _template_body(disk_layout, **overrides) -> dict:
    body = {
        "name": "test-template",
        "disk_layout_id": str(disk_layout.id),
        "cpu_count": 2,
        "ram_mb": 4096,
        "disk_size_gb": 80,
        "network_name": "VM Network",
        "local_admin_password": "P@ssw0rd1!",
    }
    body.update(overrides)
    return body


async def test_custom_admin_off_by_default_forces_builtin_administrator(test_client, db_session):
    """A caller can send whatever local_admin_username they like, if
    custom_admin_enabled isn't set (or is false), the route normalizes it
    back to "Administrator" so the answer file and every downstream WinRM
    call agree on which account actually exists."""
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)

    resp = await test_client.post(
        f"/api/organizations/{org.id}/templates",
        json=_template_body(disk_layout, local_admin_username="whatever"),
        headers=await auth_headers(operator),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["custom_admin_enabled"] is False
    assert body["local_admin_username"] == "Administrator"


async def test_custom_admin_on_rejects_reserved_name(test_client, db_session):
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)

    resp = await test_client.post(
        f"/api/organizations/{org.id}/templates",
        json=_template_body(disk_layout, custom_admin_enabled=True, local_admin_username="Administrator"),
        headers=await auth_headers(operator),
    )
    assert resp.status_code == 400
    assert "reserved" in resp.json()["detail"].lower()


async def test_custom_admin_on_accepts_a_real_username(test_client, db_session):
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)

    resp = await test_client.post(
        f"/api/organizations/{org.id}/templates",
        json=_template_body(disk_layout, custom_admin_enabled=True, local_admin_username="svcwinadmin"),
        headers=await auth_headers(operator),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["custom_admin_enabled"] is True
    assert body["local_admin_username"] == "svcwinadmin"


async def test_patch_toggling_custom_admin_on_without_a_new_username_is_rejected(test_client, db_session):
    """The existing row's local_admin_username is "Administrator" (the
    off-by-default state); flipping the toggle on in a patch that doesn't
    also supply a new username must not silently keep "Administrator" as
    the "custom" account, that's the exact name being disabled."""
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)

    create = await test_client.post(
        f"/api/organizations/{org.id}/templates",
        json=_template_body(disk_layout),
        headers=await auth_headers(operator),
    )
    template_id = create.json()["id"]

    resp = await test_client.patch(
        f"/api/organizations/{org.id}/templates/{template_id}",
        json={"custom_admin_enabled": True},
        headers=await auth_headers(operator),
    )
    assert resp.status_code == 400

    resp = await test_client.patch(
        f"/api/organizations/{org.id}/templates/{template_id}",
        json={"custom_admin_enabled": True, "local_admin_username": "svcwinadmin"},
        headers=await auth_headers(operator),
    )
    assert resp.status_code == 200
    assert resp.json()["local_admin_username"] == "svcwinadmin"
