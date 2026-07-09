from sqlalchemy import select

from app.models.iso_asset import IsoAsset
from app.models.template import DeploymentTemplate
from app.models.user import Role

from tests.conftest import (
    auth_headers,
    make_disk_layout,
    make_iso_asset,
    make_organization,
    make_template,
    make_user,
)


async def test_delete_iso_referenced_by_template_clears_the_reference_instead_of_failing(test_client, db_session):
    """Deleting an ISO asset used to hit deployment_templates_iso_asset_id_fkey
    with no ON DELETE clause: Postgres blocked the delete outright with an
    IntegrityError, which the frontend's uncaught promise rejection turned
    into "click delete, nothing happens." The UI already promised ("Templates
    referencing it will refuse to deploy until a new ISO is attached") a
    behavior the schema never actually implemented."""
    org = await make_organization(db_session)
    disk_layout = await make_disk_layout(db_session, org)
    iso_asset = await make_iso_asset(db_session, org)
    template = await make_template(db_session, org, disk_layout, iso_asset)
    operator = await make_user(db_session, org=org, org_role=Role.OPERATOR)

    delete = await test_client.delete(
        f"/api/organizations/{org.id}/iso-assets/{iso_asset.id}", headers=await auth_headers(operator)
    )
    assert delete.status_code == 204

    # fresh select()s rather than Session.get()/refresh(), which would
    # otherwise happily hand back pre-delete state straight from the
    # identity map without re-checking the database
    result = await db_session.execute(select(IsoAsset).where(IsoAsset.id == iso_asset.id))
    assert result.scalars().first() is None

    result = await db_session.execute(select(DeploymentTemplate).where(DeploymentTemplate.id == template.id))
    surviving = result.scalars().first()
    assert surviving is not None
    assert surviving.iso_asset_id is None
