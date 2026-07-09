from app.models.app_asset import AppAsset, AppKind
from app.models.user import Role

from tests.conftest import (
    auth_headers,
    make_deployment,
    make_disk_layout,
    make_hypervisor_host,
    make_iso_asset,
    make_organization,
    make_template,
    make_user,
)


async def make_app_asset(db_session, org, kind: AppKind = AppKind.EXE, storage_path: str = "/data/app_assets/test.exe") -> AppAsset:
    app_asset = AppAsset(
        org_id=org.id if org else None,
        kind=kind,
        name="Test Agent",
        filename="agent.exe",
        storage_path=storage_path,
        checksum_sha256="0" * 64,
        size_bytes=1024,
        default_install_args="/S",
    )
    db_session.add(app_asset)
    await db_session.commit()
    await db_session.refresh(app_asset)
    return app_asset


async def test_create_and_list_app_asset(test_client, db_session):
    org = await make_organization(db_session)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)

    resp = await test_client.post(
        f"/api/organizations/{org.id}/app-assets",
        json={"name": "Datto RMM Agent", "filename": "AgentSetup.exe", "kind": "exe", "default_install_args": "/S"},
        headers=await auth_headers(operator),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Datto RMM Agent"
    assert body["kind"] == "exe"
    assert body["upload_status"] == "pending"

    listed = await test_client.get(f"/api/organizations/{org.id}/app-assets", headers=await auth_headers(operator))
    assert listed.status_code == 200
    assert any(a["id"] == body["id"] for a in listed.json())


async def test_delete_app_asset_removes_file(test_client, db_session, tmp_path):
    org = await make_organization(db_session)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)
    real_file = tmp_path / "agent.exe"
    real_file.write_bytes(b"fake installer bytes")
    app_asset = await make_app_asset(db_session, org, storage_path=str(real_file))

    resp = await test_client.delete(
        f"/api/organizations/{org.id}/app-assets/{app_asset.id}", headers=await auth_headers(operator)
    )
    assert resp.status_code == 204
    assert not real_file.exists()


async def test_download_requires_matching_deployment_token(test_client, db_session, tmp_path):
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    iso_asset = await make_iso_asset(db_session, org)
    template = await make_template(db_session, org, disk_layout, iso_asset)
    host = await make_hypervisor_host(db_session, org)
    user = await make_user(db_session, org=org, org_role=Role.OPERATOR)
    deployment = await make_deployment(db_session, org, template, host, user)

    real_file = tmp_path / "agent.exe"
    real_file.write_bytes(b"fake installer bytes")
    app_asset = await make_app_asset(db_session, org, storage_path=str(real_file))

    # No token set on the deployment yet (app installs haven't started): 404
    no_token = await test_client.get(
        f"/api/deployments/{deployment.id}/app-assets/{app_asset.id}/download?token=whatever"
    )
    assert no_token.status_code == 404

    deployment.app_asset_access_token = "the-real-token"
    await db_session.commit()

    wrong_token = await test_client.get(
        f"/api/deployments/{deployment.id}/app-assets/{app_asset.id}/download?token=not-it"
    )
    assert wrong_token.status_code == 403

    right_token = await test_client.get(
        f"/api/deployments/{deployment.id}/app-assets/{app_asset.id}/download?token=the-real-token"
    )
    assert right_token.status_code == 200
    assert right_token.content == b"fake installer bytes"


async def test_download_rejects_app_asset_from_a_different_org(test_client, db_session, tmp_path):
    org_a = await make_organization(db_session)
    org_b = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org_a)
    iso_asset = await make_iso_asset(db_session, org_a)
    template = await make_template(db_session, org_a, disk_layout, iso_asset)
    host = await make_hypervisor_host(db_session, org_a)
    user = await make_user(db_session, org=org_a, org_role=Role.OPERATOR)
    deployment = await make_deployment(db_session, org_a, template, host, user)
    deployment.app_asset_access_token = "the-real-token"
    await db_session.commit()

    real_file = tmp_path / "agent.exe"
    real_file.write_bytes(b"fake installer bytes")
    other_org_app_asset = await make_app_asset(db_session, org_b, storage_path=str(real_file))

    resp = await test_client.get(
        f"/api/deployments/{deployment.id}/app-assets/{other_org_app_asset.id}/download?token=the-real-token"
    )
    assert resp.status_code == 404
