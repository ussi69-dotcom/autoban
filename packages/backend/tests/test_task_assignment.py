from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.v1.auth import get_current_user
from app.database import AsyncSessionLocal, init_db
from app.main import app
from app.models import AgentInstance, AgentStatus, OrgMember, Organization, Project, Session, Task, User
from app.models.task import TaskPriority as TaskPriorityEnum
from app.models.task import TaskStatus as TaskStatusEnum


@pytest.mark.asyncio
async def test_assign_agent_creates_session() -> None:
    try:
        await init_db()
    except Exception:
        pytest.skip("Database not available")

    unique_suffix = uuid4().hex[:8]

    async with AsyncSessionLocal() as db:
        user = User(email=f"assigner-{unique_suffix}@example.com", name="Assigner")
        org = Organization(
            name="Assign Org",
            slug=f"assign-org-{unique_suffix}",
            plan="free",
        )
        db.add_all([user, org])
        await db.flush()

        member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
        project = Project(org_id=org.id, name="Assign Project", created_by=user.id)
        db.add_all([member, project])
        await db.flush()

        task = Task(
            project_id=project.id,
            title="Assignment Task",
            status=TaskStatusEnum.TODO,
            priority=TaskPriorityEnum.MEDIUM,
            created_by=user.id,
        )
        agent = AgentInstance(
            agent_type="custom",
            model="custom",
            status=AgentStatus.IDLE,
        )

        db.add_all([task, agent])
        await db.commit()

        task_id = str(task.id)
        agent_id = str(agent.id)

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        transport = ASGITransport(app=app, lifespan="on")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/tasks/{task_id}/assign",
                json={"agentId": agent_id, "auto_start": True},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["assigned_agent"]["id"] == agent_id
    assert payload["session_id"]

    async with AsyncSessionLocal() as db:
        session_result = await db.execute(
            select(Session).where(Session.task_id == task.id)
        )
        session = session_result.scalar_one_or_none()
        assert session is not None
        assert str(session.agent_id) == agent_id

        task_result = await db.execute(select(Task).where(Task.id == task.id))
        assigned_task = task_result.scalar_one()
        assert str(assigned_task.assigned_agent_id) == agent_id

        await db.execute(delete(Session).where(Session.task_id == task.id))
        await db.execute(delete(Task).where(Task.id == task.id))
        await db.execute(delete(AgentInstance).where(AgentInstance.id == agent.id))
        await db.execute(delete(Project).where(Project.id == project.id))
        await db.execute(
            delete(OrgMember).where(
                OrgMember.org_id == org.id,
                OrgMember.user_id == user.id,
            )
        )
        await db.execute(delete(Organization).where(Organization.id == org.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()
