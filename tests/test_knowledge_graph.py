import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_graph_service import KnowledgeGraphService


@pytest.mark.asyncio
async def test_create_node(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    node = await svc.create_node(None, "concept", "Test Concept", "Some content")
    assert node.node_id
    assert node.node_type == "concept"
    assert node.title == "Test Concept"
    assert node.content == "Some content"


@pytest.mark.asyncio
async def test_create_node_invalid_type(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    with pytest.raises(ValueError, match="Invalid node_type"):
        await svc.create_node(None, "invalid_type", "test")


@pytest.mark.asyncio
async def test_get_node(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    node = await svc.create_node(None, "concept", "My Concept")
    fetched = await svc.get_node(node.node_id)
    assert fetched is not None
    assert fetched.node_id == node.node_id
    assert fetched.title == "My Concept"


@pytest.mark.asyncio
async def test_get_node_not_found(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    fetched = await svc.get_node("nonexistent")
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_node(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    node = await svc.create_node(None, "concept", "Delete me")
    assert await svc.delete_node(node.node_id) is True
    assert await svc.get_node(node.node_id) is None


@pytest.mark.asyncio
async def test_delete_node_not_found(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    assert await svc.delete_node("nonexistent") is False


@pytest.mark.asyncio
async def test_create_edge(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "Node A")
    b = await svc.create_node(None, "concept", "Node B")
    edge = await svc.create_edge(a.node_id, b.node_id, "related_to", 0.8)
    assert edge.edge_id
    assert edge.source_node_id == a.node_id
    assert edge.target_node_id == b.node_id
    assert edge.relationship_type == "related_to"
    assert edge.weight == 0.8


@pytest.mark.asyncio
async def test_create_edge_invalid_relationship(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    b = await svc.create_node(None, "concept", "B")
    with pytest.raises(ValueError, match="Invalid relationship_type"):
        await svc.create_edge(a.node_id, b.node_id, "invalid_rel")


@pytest.mark.asyncio
async def test_create_edge_source_not_found(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    b = await svc.create_node(None, "concept", "B")
    with pytest.raises(ValueError, match="Source node"):
        await svc.create_edge("nonexistent", b.node_id, "related_to")


@pytest.mark.asyncio
async def test_create_edge_target_not_found(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    with pytest.raises(ValueError, match="Target node"):
        await svc.create_edge(a.node_id, "nonexistent", "related_to")


@pytest.mark.asyncio
async def test_get_node_edges(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    b = await svc.create_node(None, "concept", "B")
    c = await svc.create_node(None, "concept", "C")
    await svc.create_edge(a.node_id, b.node_id, "leads_to")
    await svc.create_edge(c.node_id, a.node_id, "related_to")

    result = await svc.get_node_edges(a.node_id, "both")
    assert len(result["outgoing"]) == 1
    assert result["outgoing"][0]["target_node_id"] == b.node_id
    assert len(result["incoming"]) == 1
    assert result["incoming"][0]["source_node_id"] == c.node_id

    out_only = await svc.get_node_edges(a.node_id, "outgoing")
    assert len(out_only["outgoing"]) == 1
    assert len(out_only["incoming"]) == 0

    in_only = await svc.get_node_edges(a.node_id, "incoming")
    assert len(in_only["outgoing"]) == 0
    assert len(in_only["incoming"]) == 1


@pytest.mark.asyncio
async def test_list_project_nodes(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    n1 = await svc.create_node("proj-1", "task", "Task 1")
    n2 = await svc.create_node("proj-1", "decision", "Decision 1")
    n3 = await svc.create_node("proj-2", "concept", "Other")

    nodes = await svc.list_project_nodes("proj-1")
    assert len(nodes) == 2
    assert {n["title"] for n in nodes} == {"Task 1", "Decision 1"}

    filtered = await svc.list_project_nodes("proj-1", "task")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Task 1"


@pytest.mark.asyncio
async def test_find_paths(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    b = await svc.create_node(None, "concept", "B")
    c = await svc.create_node(None, "concept", "C")
    d = await svc.create_node(None, "concept", "D")
    await svc.create_edge(a.node_id, b.node_id, "leads_to")
    await svc.create_edge(b.node_id, c.node_id, "leads_to")
    await svc.create_edge(c.node_id, d.node_id, "leads_to")

    paths = await svc.find_paths(a.node_id, d.node_id, max_depth=5)
    assert len(paths) >= 1
    path = paths[0]
    assert len(path) == 3
    assert path[0]["source"] == a.node_id
    assert path[-1]["target"] == d.node_id


@pytest.mark.asyncio
async def test_find_paths_disconnected(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    b = await svc.create_node(None, "concept", "B")
    paths = await svc.find_paths(a.node_id, b.node_id, max_depth=5)
    assert len(paths) == 0


@pytest.mark.asyncio
async def test_impact_analysis(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "Root")
    b = await svc.create_node(None, "concept", "Child 1")
    c = await svc.create_node(None, "concept", "Child 2")
    d = await svc.create_node(None, "concept", "Grandchild")
    await svc.create_edge(a.node_id, b.node_id, "leads_to")
    await svc.create_edge(a.node_id, c.node_id, "leads_to")
    await svc.create_edge(b.node_id, d.node_id, "leads_to")

    impact = await svc.get_impact_analysis(a.node_id, max_depth=3)
    affected = {i["node_id"] for i in impact}
    assert b.node_id in affected
    assert c.node_id in affected
    assert d.node_id in affected


@pytest.mark.asyncio
async def test_root_cause_analysis(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "Root Cause")
    b = await svc.create_node(None, "concept", "Intermediate")
    c = await svc.create_node(None, "concept", "Issue")
    await svc.create_edge(a.node_id, b.node_id, "leads_to")
    await svc.create_edge(b.node_id, c.node_id, "leads_to")

    causes = await svc.get_root_cause_analysis(c.node_id, max_depth=3)
    cause_ids = {i["node_id"] for i in causes}
    assert a.node_id in cause_ids
    assert b.node_id in cause_ids


@pytest.mark.asyncio
async def test_project_graph(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    n1 = await svc.create_node("proj-x", "task", "Task 1")
    n2 = await svc.create_node("proj-x", "decision", "Decision 1")
    n3 = await svc.create_node("proj-x", "lesson", "Lesson 1")
    n4 = await svc.create_node("other-proj", "concept", "Other")
    await svc.create_edge(n1.node_id, n2.node_id, "addresses")
    await svc.create_edge(n2.node_id, n3.node_id, "generates")
    await svc.create_edge(n4.node_id, n1.node_id, "related_to")

    graph = await svc.get_project_graph("proj-x")
    assert len(graph["nodes"]) == 3
    node_ids = {n["node_id"] for n in graph["nodes"]}
    assert n1.node_id in node_ids
    assert n2.node_id in node_ids
    assert n3.node_id in node_ids
    assert n4.node_id not in node_ids

    assert len(graph["edges"]) == 2
    edge_ids = {e["edge_id"] for e in graph["edges"]}
    assert n4.node_id not in {e["source_node_id"] for e in graph["edges"]}


@pytest.mark.asyncio
async def test_create_node_with_metadata(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    node = await svc.create_node(
        None, "task", "Complex Task",
        "Details", {"priority": "high", "tags": ["urgent"]},
    )
    assert node.metadata_json is not None
    import json
    meta = json.loads(node.metadata_json)
    assert meta["priority"] == "high"
    assert meta["tags"] == ["urgent"]


@pytest.mark.asyncio
async def test_create_edge_with_metadata(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    b = await svc.create_node(None, "concept", "B")
    edge = await svc.create_edge(
        a.node_id, b.node_id, "depends_on", 0.5,
        {"source": "user", "confidence": 0.9},
    )
    import json
    meta = json.loads(edge.metadata_json)
    assert meta["source"] == "user"
    assert meta["confidence"] == 0.9


@pytest.mark.asyncio
async def test_auto_index_project(session: AsyncSession):
    from app.models.project import Project
    from app.services.knowledge_graph_service import KnowledgeGraphService

    project = Project(name="Auto Index Test", description="Test")
    session.add(project)
    await session.flush()
    pid = project.project_id

    from app.models.task import Task
    from app.models.decision import Decision
    from app.models.lesson import Lesson

    session.add(Task(project_id=pid, title="Task 1", description="Do thing"))
    session.add(Decision(project_id=pid, question="Which approach?", selected="Approach A"))
    session.add(Lesson(project_id=pid, problem="Bug in X", solution="Fix Y"))
    await session.flush()

    svc = KnowledgeGraphService(session)
    count = await svc.auto_index_project(pid, session)
    assert count == 3

    nodes = await svc.list_project_nodes(pid)
    assert len(nodes) == 3
    types = {n["node_type"] for n in nodes}
    assert types == {"task", "decision", "lesson"}


@pytest.mark.asyncio
async def test_create_node_with_project_id(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    node = await svc.create_node("proj-123", "task", "Scoped Task")
    assert node.project_id == "proj-123"


@pytest.mark.asyncio
async def test_get_node_edges_no_edges(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    node = await svc.create_node(None, "concept", "Alone")
    result = await svc.get_node_edges(node.node_id)
    assert result["outgoing"] == []
    assert result["incoming"] == []


@pytest.mark.asyncio
async def test_edge_cascade_on_node_delete(session: AsyncSession):
    svc = KnowledgeGraphService(session)
    a = await svc.create_node(None, "concept", "A")
    b = await svc.create_node(None, "concept", "B")
    await svc.create_edge(a.node_id, b.node_id, "related_to")

    assert await svc.delete_node(a.node_id) is True

    result = await svc.get_node_edges(b.node_id, "incoming")
    assert result["incoming"] == []
