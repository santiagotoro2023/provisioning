from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.disk_layout import DiskLayout
from app.models.hypervisor import HypervisorHost
from app.models.iso_asset import IsoAsset
from app.models.user import Role, User, UserOrgRole

from tests.conftest import auth_headers, make_disk_layout, make_hypervisor_host, make_iso_asset, make_organization, make_user


async def test_delete_organization_cascades_and_keeps_audit_log(test_client, db_session):
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    iso_asset = await make_iso_asset(db_session, org)
    host = await make_hypervisor_host(db_session, org)
    org_user = await make_user(db_session, org=org, org_role=Role.OPERATOR)
    global_admin = await make_user(db_session, global_role=Role.ADMIN)

    delete = await test_client.delete(f"/api/organizations/{org.id}", headers=await auth_headers(global_admin))
    assert delete.status_code == 204

    # fresh select()s rather than Session.get(), which would otherwise
    # happily hand back the pre-delete objects straight from the identity
    # map without ever re-checking the database
    async def exists(model, *where) -> bool:
        result = await db_session.execute(select(model).where(*where))
        return result.scalars().first() is not None

    assert not await exists(DiskLayout, DiskLayout.id == disk_layout.id)
    assert not await exists(IsoAsset, IsoAsset.id == iso_asset.id)
    assert not await exists(HypervisorHost, HypervisorHost.id == host.id)
    assert not await exists(UserOrgRole, UserOrgRole.user_id == org_user.id, UserOrgRole.org_id == org.id)
    # the user account itself isn't touched, only its role assignment to the deleted org
    assert await exists(User, User.id == org_user.id)

    audit_rows = (await db_session.execute(select(AuditLog).where(AuditLog.action == "organization.delete"))).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].org_id is None  # ON DELETE SET NULL, row itself survives
    assert audit_rows[0].detail["name"] == org.name


async def test_delete_organization_requires_global_admin(test_client, db_session):
    org = await make_organization(db_session)
    org_admin = await make_user(db_session, org=org, org_role=Role.ADMIN)

    delete = await test_client.delete(f"/api/organizations/{org.id}", headers=await auth_headers(org_admin))
    assert delete.status_code == 403
