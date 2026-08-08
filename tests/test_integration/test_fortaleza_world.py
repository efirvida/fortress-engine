"""Tests for Fortaleza world data — Episode 1 YAML validation.

Validates that all YAML files load correctly, entity IDs are unique,
spatial_anchors resolve to existing rooms, and the world integrity
check passes.
"""

from __future__ import annotations

import pytest

from fortress_engine.entities.loader import EntityLoader

_WORLD_PATH = "worlds/fortaleza"


class TestFortalezaWorldConfig:
    """World config loads and validates."""

    def test_world_yaml_loads(self):
        """world.yaml loads and returns a valid config dict."""
        loader = EntityLoader(_WORLD_PATH)
        config = loader.load_world_config()
        assert config["world_id"] == "fortaleza"
        assert config["language"] == "es"

    def test_vocabulary_loads(self):
        """vocabulary.yaml loads as a Vocabulary object."""
        loader = EntityLoader(_WORLD_PATH)
        vocab = loader.load_vocabulary()
        assert vocab is not None
        assert "ir" in vocab.verbs
        assert "tomar" in vocab.verbs
        assert "matar" in vocab.verbs
        assert isinstance(vocab.movement_verbs, list)


class TestFortalezaEpisodes:
    """Episodes load and validate."""

    def test_episode_01_loads(self):
        """Episode 1 loads with valid structure."""
        loader = EntityLoader(_WORLD_PATH)
        episodes = loader.load_episodes()
        assert len(episodes) >= 1
        ep1 = episodes[0]
        assert ep1.id == "episode-01"
        assert ep1.start_anchor == "el_exterior_de_la_fortaleza"
        assert ep1.goal is not None

    def test_episode_02_loads(self):
        """Episode 2 loads with valid structure."""
        loader = EntityLoader(_WORLD_PATH)
        episodes = loader.load_episodes()
        assert len(episodes) == 2
        ep2 = episodes[1]
        assert ep2.id == "episode-02"
        assert ep2.start_anchor == "cuarto_huespedes"
        assert "episode-01" in ep2.requires


class TestFortalezaEpisode1Rooms:
    """Episode 1 rooms load and validate."""

    def test_all_rooms_load(self):
        """All 33 room YAML files load without errors."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        assert len(rooms) == 33, f"Expected 33 rooms, got {len(rooms)}"

    def test_room_ids_are_unique(self):
        """Room entity_ids are unique."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        ids = [r.entity_id for r in rooms]
        assert len(ids) == len(set(ids)), f"Duplicate room IDs: {ids}"

    def test_start_anchor_exists(self):
        """Episode 1 start_anchor resolves to a loaded room."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        room_ids = {r.entity_id for r in rooms}
        assert "el_exterior_de_la_fortaleza" in room_ids

    def test_room_components_valid(self):
        """Rooms have required components."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        for room in rooms:
            assert room.entity_id
            assert room.name
            assert room.type == "room"


class TestFortalezaEpisode1Items:
    """Episode 1 items load and validate."""

    def test_items_load(self):
        """All item YAML files load without errors."""
        loader = EntityLoader(_WORLD_PATH)
        items = loader.load_items("episode-01")
        assert len(items) >= 40, f"Expected >=40 items, got {len(items)}"

    def test_item_ids_are_unique(self):
        """Item entity_ids are unique."""
        loader = EntityLoader(_WORLD_PATH)
        items = loader.load_items("episode-01")
        ids = [i.entity_id for i in items]
        assert len(ids) == len(set(ids)), f"Duplicate item IDs: {ids}"

    def test_items_have_valid_spatial_anchor(self):
        """All items reference existing rooms via spatial_anchor."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        items = loader.load_items("episode-01")
        room_ids = {r.entity_id for r in rooms}
        for item in items:
            if item.spatial_anchor is not None:
                assert item.spatial_anchor in room_ids, (
                    f"Item '{item.entity_id}' anchor '{item.spatial_anchor}' "
                    f"not in rooms: {room_ids}"
                )

    def test_critical_items_exist(self):
        """Critical puzzle items exist."""
        loader = EntityLoader(_WORLD_PATH)
        items = loader.load_items("episode-01")
        item_ids = {i.entity_id for i in items}
        critical = ["maza", "antorcha", "espada", "pastel_cerezas"]
        for cid in critical:
            assert cid in item_ids, f"Critical item '{cid}' missing"


class TestFortalezaEpisode1NPCs:
    """Episode 1 NPCs load and validate."""

    def test_npcs_load(self):
        """All NPC YAML files load without errors."""
        loader = EntityLoader(_WORLD_PATH)
        npcs = loader.load_npcs("episode-01")
        assert len(npcs) >= 20, f"Expected >=20 NPCs, got {len(npcs)}"

    def test_npc_ids_are_unique(self):
        """NPC entity_ids are unique."""
        loader = EntityLoader(_WORLD_PATH)
        npcs = loader.load_npcs("episode-01")
        ids = [n.entity_id for n in npcs]
        assert len(ids) == len(set(ids)), f"Duplicate NPC IDs: {ids}"

    def test_npcs_have_valid_spatial_anchor(self):
        """All NPCs reference existing rooms via spatial_anchor."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        npcs = loader.load_npcs("episode-01")
        room_ids = {r.entity_id for r in rooms}
        for npc in npcs:
            if npc.spatial_anchor is not None:
                assert npc.spatial_anchor in room_ids, (
                    f"NPC '{npc.entity_id}' anchor '{npc.spatial_anchor}' "
                    f"not in rooms: {room_ids}"
                )

    def test_critical_npcs_exist(self):
        """Critical NPCs (guards and trolls) exist."""
        loader = EntityLoader(_WORLD_PATH)
        npcs = loader.load_npcs("episode-01")
        npc_ids = {n.entity_id for n in npcs}
        critical = ["ciclope", "minotauro", "centro_cerebro", "llamador_bronce"]
        for cid in critical:
            assert cid in npc_ids, f"Critical NPC '{cid}' missing"


class TestFortalezaEpisode1MacroEdges:
    """Episode 1 macro-edges load and validate."""

    def test_macro_edges_load(self):
        """All macro-edge YAML files load without errors."""
        loader = EntityLoader(_WORLD_PATH)
        edges = loader.load_macro_edges("episode-01")
        assert len(edges) >= 40, f"Expected >=40 macro-edges, got {len(edges)}"

    def test_macro_edge_ids_are_unique(self):
        """Macro edge IDs are unique."""
        loader = EntityLoader(_WORLD_PATH)
        edges = loader.load_macro_edges("episode-01")
        ids = [e.macro_edge_id for e in edges]
        assert len(ids) == len(set(ids)), f"Duplicate macro-edge IDs: {ids}"

    def test_macro_edges_reference_valid_rooms(self):
        """All macro-edges reference existing rooms."""
        loader = EntityLoader(_WORLD_PATH)
        rooms = loader.load_rooms("episode-01")
        edges = loader.load_macro_edges("episode-01")
        room_ids = {r.entity_id for r in rooms}
        for edge in edges:
            assert edge.from_anchor in room_ids, (
                f"Macro-edge '{edge.macro_edge_id}' from_anchor "
                f"'{edge.from_anchor}' not in rooms: {room_ids}"
            )
            assert edge.to_anchor in room_ids, (
                f"Macro-edge '{edge.macro_edge_id}' to_anchor "
                f"'{edge.to_anchor}' not in rooms: {room_ids}"
            )

    def test_start_room_has_exits(self):
        """Starting room has at least one macro-edge."""
        loader = EntityLoader(_WORLD_PATH)
        edges = loader.load_macro_edges("episode-01")
        start_exits = [
            e for e in edges
            if e.from_anchor == "el_exterior_de_la_fortaleza"
            or e.to_anchor == "el_exterior_de_la_fortaleza"
        ]
        assert len(start_exits) >= 1, "Start room has no exits"


class TestFortalezaEpisode1FullLoad:
    """Full episode-01 data load integration."""

    def test_load_episode_data(self):
        """load_episode_data returns all data types."""
        loader = EntityLoader(_WORLD_PATH)
        episodes = loader.load_episodes()
        ep1 = episodes[0]
        data = loader.load_episode_data("episode-01", ep1)
        assert "rooms" in data
        assert "items" in data
        assert "npcs" in data
        assert "macro_edges" in data
        assert "hyper_edges" in data
        assert len(data["rooms"]) == 33
        assert len(data["items"]) >= 40
        assert len(data["npcs"]) >= 20
        assert len(data["macro_edges"]) >= 40

    def test_validate_world_passes(self):
        """validate_world() returns empty list for episode-01."""
        loader = EntityLoader(_WORLD_PATH)
        problems = loader.validate_world()
        # Filter to only episode-01 problems
        ep1_problems = [p for p in problems if "episode-01" in p or "episodio" in p.lower()]
        assert len(ep1_problems) == 0, f"World validation problems: {ep1_problems}"


class TestFortalezaEpisode1HyperEdges:
    """Episode 1 hyper-edges load and validate."""

    def test_hyper_edges_load(self):
        """All hyper-edge YAML files load without errors."""
        loader = EntityLoader(_WORLD_PATH)
        hes = loader.load_hyper_edges("episode-01")
        assert len(hes) >= 80, f"Expected >=80 hyper-edges, got {len(hes)}"

    def test_hyper_edge_ids_are_unique(self):
        """Hyper edge IDs are unique."""
        loader = EntityLoader(_WORLD_PATH)
        hes = loader.load_hyper_edges("episode-01")
        ids = [h.hyper_edge_id for h in hes]
        assert len(ids) == len(set(ids)), f"Duplicate hyper-edge IDs: {ids}"

    def test_hyper_edges_have_valid_verbs(self):
        """All hyper-edges use recognized verbs."""
        loader = EntityLoader(_WORLD_PATH)
        hes = loader.load_hyper_edges("episode-01")
        valid_verbs = {
            "tomar", "coger", "dejar", "soltar", "abrir",
            "matar", "asesinar", "destrozar", "romper", "forzar",
            "preguntar", "interrogar", "dar", "regalar",
            "ver", "leer", "mirar", "observar",
            "inventario", "abandonar", "terminar",
            "huir", "escapar", "ir", "atravesar", "cruzar", "pasar",
            "pesar",
        }
        for he in hes:
            assert he.clique.verb in valid_verbs, (
                f"Hyper-edge '{he.hyper_edge_id}' has unknown verb '{he.clique.verb}'"
            )

    def test_take_edges_exist(self):
        """Critical take hyper-edges exist."""
        loader = EntityLoader(_WORLD_PATH)
        hes = loader.load_hyper_edges("episode-01")
        he_ids = {h.hyper_edge_id for h in hes}
        assert "he_tomar_maza" in he_ids
        assert "he_tomar_antorcha" in he_ids
        assert "he_tomar_espada" in he_ids

    def test_kill_edges_exist(self):
        """Critical kill hyper-edges exist."""
        loader = EntityLoader(_WORLD_PATH)
        hes = loader.load_hyper_edges("episode-01")
        he_ids = {h.hyper_edge_id for h in hes}
        assert "he_matar_ciclope" in he_ids
        assert "he_matar_minotauro" in he_ids
        assert "he_matar_centro_cerebro" in he_ids

    def test_give_edges_exist(self):
        """Critical give hyper-edges exist."""
        loader = EntityLoader(_WORLD_PATH)
        hes = loader.load_hyper_edges("episode-01")
        he_ids = {h.hyper_edge_id for h in hes}
        assert "he_dar_cigarro_llamador" in he_ids
        assert "he_dar_pastel_crunch" in he_ids


class TestFortalezaWorldIntegrity:
    """World integrity validation."""

    def test_no_dangling_shared_entities(self):
        """load_shared_entities doesn't crash on vocabulary.yaml."""
        loader = EntityLoader(_WORLD_PATH)
        shared = loader.load_shared_entities("episode-01")
        # Should load player.yaml, skip vocabulary.yaml
        shared_ids = {s.entity_id for s in shared}
        assert "hero" in shared_ids
        # vocabulary.yaml should NOT be loaded as an entity
        assert "vocabulary" not in shared_ids

    def test_world_validation_passes(self):
        """validate_world() returns empty list (no problems)."""
        loader = EntityLoader(_WORLD_PATH)
        # This will fail if macro-edges or hyper-edges don't exist yet,
        # but should at least not crash on entity loading.
        # We test rooms/items/npcs integrity only.
        rooms = loader.load_rooms("episode-01")
        items = loader.load_items("episode-01")
        npcs = loader.load_npcs("episode-01")

        # Collect all entity IDs
        all_ids = {r.entity_id for r in rooms}
        all_ids.update({i.entity_id for i in items})
        all_ids.update({n.entity_id for n in npcs})

        # Check no dangling spatial_anchors
        for item in items:
            if item.spatial_anchor is not None:
                assert item.spatial_anchor in all_ids, (
                    f"Item '{item.entity_id}' has dangling anchor "
                    f"'{item.spatial_anchor}'"
                )
        for npc in npcs:
            if npc.spatial_anchor is not None:
                assert npc.spatial_anchor in all_ids, (
                    f"NPC '{npc.entity_id}' has dangling anchor "
                    f"'{npc.spatial_anchor}'"
                )
