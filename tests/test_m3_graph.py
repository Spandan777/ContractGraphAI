from contractgraph.graph import build_dependency_graph, edges_as_dicts


def sample_clauses():
    return [
        {
            "id": "C1",
            "title": "Section 1 Payment",
            "text": "The Customer shall pay invoices within 30 days.",
            "aspects": ["payment", "obligation"],
        },
        {
            "id": "C2",
            "title": "Section 2 Payment Terms",
            "text": "Pursuant to Section 1, payment shall be made within 60 days.",
            "aspects": ["payment", "obligation"],
        },
        {
            "id": "C3",
            "title": "Section 3 Liability Exception",
            "text": "Except for fraud, liability shall not exceed USD 50,000.",
            "aspects": ["liability", "exception"],
        },
        {
            "id": "C4",
            "title": "Section 4 Liability",
            "text": "The liability cap shall survive for five years.",
            "aspects": ["liability"],
        },
        {
            "id": "C5",
            "title": "Section 5 Termination",
            "text": "Either party may terminate this agreement with notice.",
            "aspects": ["termination"],
        },
    ]


def test_graph_contains_all_clause_nodes():
    graph = build_dependency_graph(sample_clauses())
    assert set(graph.nodes) == {"C1", "C2", "C3", "C4", "C5"}


def test_explicit_reference_resolution():
    graph = build_dependency_graph(sample_clauses())
    assert any(
        data["relation"] == "explicit_reference"
        for _, _, data in graph.edges(data=True)
    )


def test_shared_aspect_and_potential_conflict():
    graph = build_dependency_graph(sample_clauses())
    relations = [data["relation"] for _, _, data in graph.edges(data=True)]
    assert "shared_aspect" in relations
    assert "potential_conflict" in relations


def test_exception_relationship():
    graph = build_dependency_graph(sample_clauses())
    assert any(
        data["relation"] == "exception_to"
        for _, _, data in graph.edges(data=True)
    )


def test_temporal_relationship():
    graph = build_dependency_graph(sample_clauses())
    assert any(
        data["relation"] == "temporal_dependency"
        for _, _, data in graph.edges(data=True)
    )


def test_graph_edges_are_auditable():
    graph = build_dependency_graph(sample_clauses())
    edges = edges_as_dicts(graph)
    assert edges
    for edge in edges:
        assert edge["source"] != edge["target"]
        assert edge["relation"]
        assert edge["reason"]
        assert edge["method"]
        assert 0 <= edge["confidence"] <= 1
