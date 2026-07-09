import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.iso_asset import IsoAsset
from app.models.org import Organization
from app.models.user import Role, User, UserOrgRole
from app.schemas.org import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.security.rbac import get_current_user, require_role
from app.services import audit

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Organization]:
    if current_user.global_role != Role.NONE:
        result = await db.execute(select(Organization))
        return list(result.scalars().all())
    result = await db.execute(
        select(Organization)
        .join(UserOrgRole, UserOrgRole.org_id == Organization.id)
        .where(UserOrgRole.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, org_scoped=False)),
) -> Organization:
    org = Organization(**body.model_dump())
    db.add(org)
    await db.flush()
    audit.record(
        db, action="organization.create", target_type="organization",
        org_id=org.id, user_id=current_user.id, target_id=org.id, detail={"name": org.name},
    )
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.READONLY)),
) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "organization not found")
    return org


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "organization not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(org, field, value)
    audit.record(
        db, action="organization.update", target_type="organization", org_id=org_id,
        user_id=current_user.id, target_id=org_id, detail={"fields": list(updates.keys())},
    )
    await db.commit()
    await db.refresh(org)
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, org_scoped=False)),
) -> None:
    """Permanently deletes an organization and everything scoped to it:
    hypervisors, disk layouts, templates, ISO assets, deployments,
    webhooks, settings, and every user's role assignment for it, via
    ON DELETE CASCADE foreign keys, in one transaction. The audit log is
    the one exception (ON DELETE SET NULL): its rows survive with org_id
    cleared, this delete action itself included, so there's still a
    record that it happened.

    ISO files on disk aren't covered by any database cascade, so they're
    unlinked explicitly first. VMs already created on the org's
    hypervisors are not touched, DeployCore has no way to reach them once
    its own record of the hypervisor connection is gone."""
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "organization not found")

    isos = await db.execute(select(IsoAsset).where(IsoAsset.org_id == org_id))
    for iso in isos.scalars().all():
        if iso.storage_path:
            Path(iso.storage_path).unlink(missing_ok=True)

    audit.record(
        db, action="organization.delete", target_type="organization", org_id=org_id,
        user_id=current_user.id, target_id=org_id, detail={"name": org.name},
    )
    await db.delete(org)
    await db.commit()
