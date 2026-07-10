from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.deployment import Deployment, DeploymentState

router = APIRouter(prefix="/api/callback", tags=["callback"])


@router.post("/{deployment_token}", status_code=status.HTTP_204_NO_CONTENT)
async def deployment_callback(deployment_token: str, db: AsyncSession = Depends(get_db)) -> None:
    """Authenticated by the single-use per-deployment token itself, not by
    a user session, the caller is the guest VM's FirstLogonCommands step,
    not an operator. Doesn't transition state itself: run_deployment
    already moves the deployment into installing_os right after it's done
    everything it can to get Setup running (see worker/tasks/provision.py),
    since there's no way to observe real progress during Setup itself, this
    callback firing is just the signal that install.wim's copy has fully
    landed and the guest is up, worker/tasks/provision.py's
    wait_for_callback polls callback_token_used (set here) for exactly
    that, and the installing_os -> post_install transition happens once
    it's actually confirmed reachable over WinRM."""
    result = await db.execute(select(Deployment).where(Deployment.callback_token == deployment_token))
    deployment = result.scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown callback token")
    if deployment.callback_token_used:
        raise HTTPException(status.HTTP_409_CONFLICT, "callback token already used")
    if deployment.state != DeploymentState.INSTALLING_OS:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"deployment is not awaiting a callback (state={deployment.state.value})"
        )

    deployment.callback_token_used = True
    await db.commit()
