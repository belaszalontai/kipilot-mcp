from __future__ import annotations

from kipilot_mcp.config import KiCadIpcConfig
from kipilot_mcp.ipc_client import ApiError, KiCadIpcClient


async def test_check_connection_uses_kicad_python_factory() -> None:
    calls: dict[str, object] = {}

    class FakeKiCad:
        def __init__(self, **kwargs: object) -> None:
            calls["kwargs"] = kwargs

        def ping(self) -> None:
            calls["ping"] = True

        def get_version(self) -> str:
            return "9.0.0"

        def get_api_version(self) -> str:
            return "1.0.0"

        def check_version(self) -> bool:
            return True

        def close(self) -> None:
            calls["closed"] = True

    client = KiCadIpcClient(
        KiCadIpcConfig(
            socket_path="test-pipe",
            api_token="test-token",
            client_name="test-client",
            timeout_ms=1234,
        ),
        kicad_factory=FakeKiCad,
    )
    result = await client.check_connection()

    assert result == {
        "ok": True,
        "socket_path": "test-pipe",
        "client_name": "test-client",
        "kicad_version": "9.0.0",
        "api_version": "1.0.0",
        "api_version_matches_binding": True,
        "message": "KiCad IPC endpoint is reachable.",
    }
    assert calls == {
        "kwargs": {
            "client_name": "test-client",
            "timeout_ms": 1234,
            "socket_path": "test-pipe",
            "kicad_token": "test-token",
        },
        "ping": True,
        "closed": True,
    }


async def test_check_connection_reports_clear_failure() -> None:
    class FailingKiCad:
        def __init__(self, **_kwargs: object) -> None:
            raise RuntimeError("KiCad is not running")

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FailingKiCad)
    result = await client.check_connection()

    assert result["ok"] is False
    assert "KiCad IPC is not reachable" in str(result["message"])
    assert result["error"] == "KiCad is not running"


async def test_get_board_summary_returns_counts() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_board_summary()

    assert result == {
        "ok": True,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "counts": {
            "footprints": 2,
            "nets": 2,
            "tracks": 1,
            "vias": 1,
            "zones": 1,
            "graphics": 2,
            "text_items": 6,
        },
        "copper_layer_count": 2,
        "active_layer": 0,
    }


async def test_get_footprints_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_footprints()

    assert result == {
        "ok": True,
        "count": 2,
        "limit": 200,
        "footprints": [
            {
                "id": "footprint-id",
                "reference": "R1",
                "value": "10k",
                "position": {
                    "x_nm": 1_500_000,
                    "y_nm": 2_500_000,
                    "x_mm": 1.5,
                    "y_mm": 2.5,
                },
                "orientation": "90deg",
                "layer": 0,
                "locked": False,
            },
            {
                "id": "footprint-b-id",
                "reference": "C5",
                "value": "100n",
                "position": {
                    "x_nm": 4_500_000,
                    "y_nm": 1_000_000,
                    "x_mm": 4.5,
                    "y_mm": 1.0,
                },
                "orientation": "0deg",
                "layer": 31,
                "locked": False,
            },
        ],
    }


async def test_get_nets_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_nets()

    assert result == {
        "ok": True,
        "count": 2,
        "limit": 200,
        "nets": [
            {
                "name": "+3V3",
                "code": 7,
            },
            {
                "name": "GND",
                "code": 1,
            },
        ],
    }


async def test_list_open_documents_returns_active_board_and_project() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.list_open_documents()

    assert result == {
        "ok": True,
        "count": 2,
        "documents": [
            {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
            {
                "type": "2",
                "board_filename": "",
                "path": "C:/demo/demo.kicad_pro",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        ],
        "source": "active_board",
    }


async def test_get_stackup_returns_serialized_layers() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_stackup()

    assert result == {
        "ok": True,
        "stackup": {
            "count": 2,
            "layers": [
                {
                    "layer": {"id": 0, "name": "F.Cu"},
                    "user_name": "F.Cu",
                    "enabled": True,
                    "type": "copper",
                    "material_name": "Copper",
                    "thickness_nm": 35_000,
                    "thickness_mm": 0.035,
                    "dielectric": None,
                },
                {
                    "layer": {"id": -1, "name": ""},
                    "user_name": "Core",
                    "enabled": True,
                    "type": "dielectric",
                    "material_name": "FR4",
                    "thickness_nm": 800_000,
                    "thickness_mm": 0.8,
                    "dielectric": {
                        "layers": [
                            {
                                "material_name": "FR4",
                                "epsilon_r": 4.2,
                                "loss_tangent": 0.02,
                                "thickness_nm": 800_000,
                                "thickness_mm": 0.8,
                            }
                        ]
                    },
                },
            ],
        },
        "copper_layer_count": 2,
        "visible_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 31, "name": "B.Cu"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
        "enabled_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 31, "name": "B.Cu"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
    }


async def test_get_tracks_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_tracks()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "tracks": [
            {
                "id": "track-id",
                "kind": "FakeTrack",
                "start": {
                    "x_nm": 1_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 1.0,
                    "y_mm": 2.0,
                },
                "end": {
                    "x_nm": 6_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 6.0,
                    "y_mm": 2.0,
                },
                "layer": {"id": 0, "name": "F.Cu"},
                "net": {"name": "+3V3", "code": 7},
                "locked": False,
                "width_nm": 250_000,
                "width_mm": 0.25,
                "length_nm": 5_000_000.0,
                "length_mm": 5.0,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 1_000_000,
                        "y_nm": 2_000_000,
                        "x_mm": 1.0,
                        "y_mm": 2.0,
                    },
                    "bottom_right": {
                        "x_nm": 6_000_000,
                        "y_nm": 2_000_000,
                        "x_mm": 6.0,
                        "y_mm": 2.0,
                    },
                },
            }
        ],
    }


async def test_get_vias_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_vias()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "vias": [
            {
                "id": "via-id",
                "kind": "FakeVia",
                "position": {
                    "x_nm": 3_000_000,
                    "y_nm": 3_500_000,
                    "x_mm": 3.0,
                    "y_mm": 3.5,
                },
                "layer": None,
                "net": {"name": "+3V3", "code": 7},
                "locked": False,
                "diameter_nm": 600_000,
                "diameter_mm": 0.6,
                "drill_diameter_nm": 300_000,
                "drill_diameter_mm": 0.3,
                "type": "through",
            }
        ],
    }


async def test_get_zones_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_zones()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "zones": [
            {
                "id": "zone-id",
                "kind": "FakeZone",
                "name": "Power Pour",
                "net": {"name": "GND", "code": 1},
                "layers": [
                    {"id": 0, "name": "F.Cu"},
                    {"id": 31, "name": "B.Cu"},
                ],
                "locked": False,
                "filled": True,
                "priority": 2,
                "type": "copper",
                "bounding_box": {
                    "top_left": {
                        "x_nm": 0,
                        "y_nm": 0,
                        "x_mm": 0.0,
                        "y_mm": 0.0,
                    },
                    "bottom_right": {
                        "x_nm": 10_000_000,
                        "y_nm": 8_000_000,
                        "x_mm": 10.0,
                        "y_mm": 8.0,
                    },
                },
                "outline": {
                    "outline": [
                        {"x_nm": 0, "y_nm": 0, "x_mm": 0.0, "y_mm": 0.0},
                        {"x_nm": 10_000_000, "y_nm": 0, "x_mm": 10.0, "y_mm": 0.0},
                        {"x_nm": 10_000_000, "y_nm": 8_000_000, "x_mm": 10.0, "y_mm": 8.0},
                        {"x_nm": 0, "y_nm": 8_000_000, "x_mm": 0.0, "y_mm": 8.0},
                    ]
                },
            }
        ],
    }


async def test_get_board_text_filters_by_query_and_layer() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_board_text(
        text_query="Mainboard v1.1",
        layer="F.SilkS",
        exact=True,
    )

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "query": {
            "text_id": None,
            "text_query": "Mainboard v1.1",
            "exact": True,
            "layer": "F.SilkS",
            "resolved_layer": {"id": 37, "name": "F.SilkS"},
        },
        "text_items": [
            {
                "id": "board-text-id",
                "kind": "FakeMutableBoardText",
                "text": "Mainboard v1.1",
                "layer": {"id": 37, "name": "F.SilkS"},
                "locked": False,
                "position": {
                    "x_nm": 20_000_000,
                    "y_nm": 10_000_000,
                    "x_mm": 20.0,
                    "y_mm": 10.0,
                },
            }
        ],
    }


async def test_get_pads_supports_net_layer_and_area_filters() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_pads(
        net_name="+3V3",
        layer="F.Cu",
        area={
            "x_min_mm": 1.5,
            "y_min_mm": 3.5,
            "x_max_mm": 2.5,
            "y_max_mm": 4.5,
        },
    )

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "query": {
            "net_name": "+3V3",
            "net": {"name": "+3V3", "code": 7},
            "layer": "F.Cu",
            "resolved_layer": {"id": 0, "name": "F.Cu"},
            "area": {
                "x_min_mm": 1.5,
                "y_min_mm": 3.5,
                "x_max_mm": 2.5,
                "y_max_mm": 4.5,
            },
        },
        "pads": [
            {
                "id": "pad-id",
                "kind": "FakePad",
                "number": "1",
                "position": {
                    "x_nm": 2_000_000,
                    "y_nm": 4_000_000,
                    "x_mm": 2.0,
                    "y_mm": 4.0,
                },
                "net": {"name": "+3V3", "code": 7},
                "pad_type": "smd",
                "layers": [
                    {"id": 0, "name": "F.Cu"},
                ],
            }
        ],
    }


async def test_get_graphics_supports_layer_and_area_filters() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_graphics(
        layer="F.SilkS",
        area={
            "x_min_mm": 0.5,
            "y_min_mm": 0.5,
            "x_max_mm": 2.5,
            "y_max_mm": 2.5,
        },
    )

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "query": {
            "layer": "F.SilkS",
            "resolved_layer": {"id": 37, "name": "F.SilkS"},
            "area": {
                "x_min_mm": 0.5,
                "y_min_mm": 0.5,
                "x_max_mm": 2.5,
                "y_max_mm": 2.5,
            },
        },
        "graphics": [
            {
                "id": "shape-silk-1",
                "kind": "FakeShape",
                "layer": {"id": 37, "name": "F.SilkS"},
                "net": None,
                "locked": False,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 1_000_000,
                        "y_nm": 1_000_000,
                        "x_mm": 1.0,
                        "y_mm": 1.0,
                    },
                    "bottom_right": {
                        "x_nm": 2_000_000,
                        "y_nm": 2_000_000,
                        "x_mm": 2.0,
                        "y_mm": 2.0,
                    },
                },
                "start": {
                    "x_nm": 1_000_000,
                    "y_nm": 1_000_000,
                    "x_mm": 1.0,
                    "y_mm": 1.0,
                },
                "end": {
                    "x_nm": 2_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 2.0,
                    "y_mm": 2.0,
                },
            }
        ],
    }


async def test_get_project_text_variables_returns_project_scope_data() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_project_text_variables()

    assert result == {
        "ok": True,
        "project": {
            "name": "demo",
            "path": "C:/demo/demo.kicad_pro",
            "document": {
                "type": "2",
                "board_filename": "",
                "path": "C:/demo/demo.kicad_pro",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "text_variables": {
            "count": 2,
            "values": {
                "AUTHOR": "KiPilot",
                "BOARD_REV": "A",
            },
            "variables": [
                {"name": "AUTHOR", "value": "KiPilot"},
                {"name": "BOARD_REV", "value": "A"},
            ],
        },
    }


async def test_expand_project_text_variables_returns_expanded_text() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.expand_project_text_variables("Rev ${BOARD_REV} by ${AUTHOR}")

    assert result == {
        "ok": True,
        "project": {
            "name": "demo",
            "path": "C:/demo/demo.kicad_pro",
            "document": {
                "type": "2",
                "board_filename": "",
                "path": "C:/demo/demo.kicad_pro",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "input_text": "Rev ${BOARD_REV} by ${AUTHOR}",
        "expanded_text": "Rev A by KiPilot",
    }


async def test_get_project_net_classes_returns_serialized_rules() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_project_net_classes()

    assert result == {
        "ok": True,
        "project": {
            "name": "demo",
            "path": "C:/demo/demo.kicad_pro",
            "document": {
                "type": "2",
                "board_filename": "",
                "path": "C:/demo/demo.kicad_pro",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "count": 2,
        "net_classes": [
            {
                "name": "Default",
                "description": "Default routing rules",
                "clearance_nm": 200_000,
                "clearance_mm": 0.2,
                "track_width_nm": 250_000,
                "track_width_mm": 0.25,
                "via_diameter_nm": 600_000,
                "via_diameter_mm": 0.6,
                "via_drill_nm": 300_000,
                "via_drill_mm": 0.3,
            },
            {
                "name": "Power",
                "description": "Power distribution",
                "clearance_nm": 300_000,
                "clearance_mm": 0.3,
                "track_width_nm": 500_000,
                "track_width_mm": 0.5,
                "via_diameter_nm": 800_000,
                "via_diameter_mm": 0.8,
                "via_drill_nm": 400_000,
                "via_drill_mm": 0.4,
            },
        ],
    }


async def test_get_board_origins_returns_grid_and_drill_positions() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_board_origins()

    assert result == {
        "ok": True,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "origins": {
            "grid": {
                "type": {"id": 1, "name": "grid"},
                "position": {
                    "x_nm": 0,
                    "y_nm": 0,
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                },
            },
            "drill": {
                "type": {"id": 2, "name": "drill"},
                "position": {
                    "x_nm": 59_900_000,
                    "y_nm": 138_400_000,
                    "x_mm": 59.9,
                    "y_mm": 138.4,
                },
            },
        },
    }


async def test_get_title_block_returns_serialized_metadata() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_title_block()

    assert result == {
        "ok": True,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "title_block": {
            "title": "Demo Board",
            "revision": "A",
            "date": "2026-05-09",
            "company": "KiPilot Labs",
            "comments": {
                "1": "Prototype",
                "2": "Internal",
            },
        },
    }


async def test_find_footprints_filters_by_reference() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.find_footprints(reference="R1")

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "query": {
            "reference": "R1",
            "footprint_id": None,
            "text_query": None,
            "layer": None,
            "resolved_layer": None,
            "area": None,
        },
        "footprints": [
            {
                "id": "footprint-id",
                "reference": "R1",
                "value": "10k",
                "position": {
                    "x_nm": 1_500_000,
                    "y_nm": 2_500_000,
                    "x_mm": 1.5,
                    "y_mm": 2.5,
                },
                "orientation": "90deg",
                "layer": 0,
                "locked": False,
            }
        ],
    }


async def test_find_footprints_supports_id_layer_name_and_area_filters() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.find_footprints(
        footprint_id="footprint-b-id",
        layer="B.Cu",
        area={
            "x_min_mm": 4.0,
            "y_min_mm": 0.5,
            "x_max_mm": 5.0,
            "y_max_mm": 1.5,
        },
    )

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "query": {
            "reference": None,
            "footprint_id": "footprint-b-id",
            "text_query": None,
            "layer": "B.Cu",
            "resolved_layer": {"id": 31, "name": "B.Cu"},
            "area": {
                "x_min_mm": 4.0,
                "y_min_mm": 0.5,
                "x_max_mm": 5.0,
                "y_max_mm": 1.5,
            },
        },
        "footprints": [
            {
                "id": "footprint-b-id",
                "reference": "C5",
                "value": "100n",
                "position": {
                    "x_nm": 4_500_000,
                    "y_nm": 1_000_000,
                    "x_mm": 4.5,
                    "y_mm": 1.0,
                },
                "orientation": "0deg",
                "layer": 31,
                "locked": False,
            },
        ],
    }


async def test_find_footprints_reports_unknown_layer() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.find_footprints(layer="Inner99.Cu")

    assert result["ok"] is False
    assert result["message"] == "Layer 'Inner99.Cu' was not found on the current board."


async def test_get_items_by_net_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_items_by_net("+3V3")

    assert result == {
        "ok": True,
        "net": {"name": "+3V3", "code": 7},
        "count": 3,
        "limit": 200,
        "item_types": None,
        "query": {
            "layer": None,
            "resolved_layer": None,
            "area": None,
        },
        "items": [
            {
                "id": "track-id",
                "kind": "FakeTrack",
                "start": {
                    "x_nm": 1_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 1.0,
                    "y_mm": 2.0,
                },
                "end": {
                    "x_nm": 6_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 6.0,
                    "y_mm": 2.0,
                },
                "layer": {"id": 0, "name": "F.Cu"},
                "net": {"name": "+3V3", "code": 7},
                "locked": False,
                "width_nm": 250_000,
                "width_mm": 0.25,
                "length_nm": 5_000_000.0,
                "length_mm": 5.0,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 1_000_000,
                        "y_nm": 2_000_000,
                        "x_mm": 1.0,
                        "y_mm": 2.0,
                    },
                    "bottom_right": {
                        "x_nm": 6_000_000,
                        "y_nm": 2_000_000,
                        "x_mm": 6.0,
                        "y_mm": 2.0,
                    },
                },
            },
            {
                "id": "via-id",
                "kind": "FakeVia",
                "position": {
                    "x_nm": 3_000_000,
                    "y_nm": 3_500_000,
                    "x_mm": 3.0,
                    "y_mm": 3.5,
                },
                "layer": None,
                "net": {"name": "+3V3", "code": 7},
                "locked": False,
                "diameter_nm": 600_000,
                "diameter_mm": 0.6,
                "drill_diameter_nm": 300_000,
                "drill_diameter_mm": 0.3,
                "type": "through",
            },
            {
                "id": "pad-id",
                "kind": "FakePad",
                "number": "1",
                "position": {
                    "x_nm": 2_000_000,
                    "y_nm": 4_000_000,
                    "x_mm": 2.0,
                    "y_mm": 4.0,
                },
                "net": {"name": "+3V3", "code": 7},
                "pad_type": "smd",
                "layers": [
                    {"id": 0, "name": "F.Cu"},
                ],
            },
        ],
    }


async def test_get_items_by_net_supports_layer_name_and_area_filters() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_items_by_net(
        "+3V3",
        layer="F.Cu",
        area={
            "x_min_mm": 2.5,
            "y_min_mm": 3.0,
            "x_max_mm": 3.5,
            "y_max_mm": 3.75,
        },
    )

    assert result == {
        "ok": True,
        "net": {"name": "+3V3", "code": 7},
        "count": 1,
        "limit": 200,
        "item_types": None,
        "query": {
            "layer": "F.Cu",
            "resolved_layer": {"id": 0, "name": "F.Cu"},
            "area": {
                "x_min_mm": 2.5,
                "y_min_mm": 3.0,
                "x_max_mm": 3.5,
                "y_max_mm": 3.75,
            },
        },
        "items": [
            {
                "id": "via-id",
                "kind": "FakeVia",
                "position": {
                    "x_nm": 3_000_000,
                    "y_nm": 3_500_000,
                    "x_mm": 3.0,
                    "y_mm": 3.5,
                },
                "net": {"name": "+3V3", "code": 7},
                "layer": None,
                "locked": False,
                "diameter_nm": 600_000,
                "diameter_mm": 0.6,
                "drill_diameter_nm": 300_000,
                "drill_diameter_mm": 0.3,
                "type": "through",
            },
        ],
    }


async def test_get_items_by_netclass_supports_layer_and_area_filters() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_items_by_netclass(
        "Power",
        layer="F.Cu",
        area={
            "x_min_mm": 2.5,
            "y_min_mm": 3.0,
            "x_max_mm": 3.5,
            "y_max_mm": 3.75,
        },
    )

    assert result == {
        "ok": True,
        "net_class": {
            "name": "Power",
            "description": "Power distribution",
            "clearance_nm": 300_000,
            "clearance_mm": 0.3,
            "track_width_nm": 500_000,
            "track_width_mm": 0.5,
            "via_diameter_nm": 800_000,
            "via_diameter_mm": 0.8,
            "via_drill_nm": 400_000,
            "via_drill_mm": 0.4,
        },
        "count": 1,
        "limit": 200,
        "item_types": None,
        "query": {
            "layer": "F.Cu",
            "resolved_layer": {"id": 0, "name": "F.Cu"},
            "area": {
                "x_min_mm": 2.5,
                "y_min_mm": 3.0,
                "x_max_mm": 3.5,
                "y_max_mm": 3.75,
            },
        },
        "items": [
            {
                "id": "via-id",
                "kind": "FakeVia",
                "position": {
                    "x_nm": 3_000_000,
                    "y_nm": 3_500_000,
                    "x_mm": 3.0,
                    "y_mm": 3.5,
                },
                "layer": None,
                "net": {"name": "+3V3", "code": 7},
                "locked": False,
                "diameter_nm": 600_000,
                "diameter_mm": 0.6,
                "drill_diameter_nm": 300_000,
                "drill_diameter_mm": 0.3,
                "type": "through",
            },
        ],
    }


async def test_get_netclass_for_nets_returns_mapping() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_netclass_for_nets(["+3V3", "GND"])

    assert result == {
        "ok": True,
        "count": 2,
        "results": [
            {
                "net": {"name": "+3V3", "code": 7},
                "net_class": {
                    "name": "Power",
                    "description": "Power distribution",
                    "clearance_nm": 300_000,
                    "clearance_mm": 0.3,
                    "track_width_nm": 500_000,
                    "track_width_mm": 0.5,
                    "via_diameter_nm": 800_000,
                    "via_diameter_mm": 0.8,
                    "via_drill_nm": 400_000,
                    "via_drill_mm": 0.4,
                },
            },
            {
                "net": {"name": "GND", "code": 1},
                "net_class": {
                    "name": "Default",
                    "description": "Default routing rules",
                    "clearance_nm": 200_000,
                    "clearance_mm": 0.2,
                    "track_width_nm": 250_000,
                    "track_width_mm": 0.25,
                    "via_diameter_nm": 600_000,
                    "via_diameter_mm": 0.6,
                    "via_drill_nm": 300_000,
                    "via_drill_mm": 0.3,
                },
            },
        ],
    }


async def test_get_connected_items_supports_layer_and_area_filters() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_connected_items(
        "track-id",
        layer="F.Cu",
        area={
            "x_min_mm": 2.5,
            "y_min_mm": 3.0,
            "x_max_mm": 3.5,
            "y_max_mm": 3.75,
        },
    )

    assert result == {
        "ok": True,
        "source_item": {
            "id": "track-id",
            "kind": "FakeTrack",
            "start": {
                "x_nm": 1_000_000,
                "y_nm": 2_000_000,
                "x_mm": 1.0,
                "y_mm": 2.0,
            },
            "end": {
                "x_nm": 6_000_000,
                "y_nm": 2_000_000,
                "x_mm": 6.0,
                "y_mm": 2.0,
            },
            "layer": {"id": 0, "name": "F.Cu"},
            "net": {"name": "+3V3", "code": 7},
            "locked": False,
            "width_nm": 250_000,
            "width_mm": 0.25,
            "length_nm": 5_000_000.0,
            "length_mm": 5.0,
            "bounding_box": {
                "top_left": {
                    "x_nm": 1_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 1.0,
                    "y_mm": 2.0,
                },
                "bottom_right": {
                    "x_nm": 6_000_000,
                    "y_nm": 2_000_000,
                    "x_mm": 6.0,
                    "y_mm": 2.0,
                },
            },
        },
        "count": 1,
        "limit": 200,
        "item_types": None,
        "query": {
            "layer": "F.Cu",
            "resolved_layer": {"id": 0, "name": "F.Cu"},
            "area": {
                "x_min_mm": 2.5,
                "y_min_mm": 3.0,
                "x_max_mm": 3.5,
                "y_max_mm": 3.75,
            },
        },
        "items": [
            {
                "id": "via-id",
                "kind": "FakeVia",
                "position": {
                    "x_nm": 3_000_000,
                    "y_nm": 3_500_000,
                    "x_mm": 3.0,
                    "y_mm": 3.5,
                },
                "layer": None,
                "net": {"name": "+3V3", "code": 7},
                "locked": False,
                "diameter_nm": 600_000,
                "diameter_mm": 0.6,
                "drill_diameter_nm": 300_000,
                "drill_diameter_mm": 0.3,
                "type": "through",
            },
        ],
    }


async def test_get_board_outline_filters_edge_cuts_shapes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_board_outline()

    assert result == {
        "ok": True,
        "count": 1,
        "layer_name": "Edge.Cuts",
        "shapes": [
            {
                "id": "shape-edge-1",
                "kind": "FakeShape",
                "layer": {"id": 44, "name": "Edge.Cuts"},
                "net": None,
                "locked": False,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 0,
                        "y_nm": 0,
                        "x_mm": 0.0,
                        "y_mm": 0.0,
                    },
                    "bottom_right": {
                        "x_nm": 10_000_000,
                        "y_nm": 0,
                        "x_mm": 10.0,
                        "y_mm": 0.0,
                    },
                },
                "start": {
                    "x_nm": 0,
                    "y_nm": 0,
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                },
                "end": {
                    "x_nm": 10_000_000,
                    "y_nm": 0,
                    "x_mm": 10.0,
                    "y_mm": 0.0,
                },
            }
        ],
        "bounding_box": {
            "top_left": {
                "x_nm": 0.0,
                "y_nm": 0.0,
                "x_mm": 0.0,
                "y_mm": 0.0,
            },
            "bottom_right": {
                "x_nm": 10_000_000.0,
                "y_nm": 0.0,
                "x_mm": 10.0,
                "y_mm": 0.0,
            },
        },
    }


async def test_board_handler_error_is_actionable() -> None:
    class ProjectManagerOnlyKiCad:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def get_board(self) -> object:
            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.GetOpenDocuments"
            )

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=ProjectManagerOnlyKiCad)
    result = await client.get_board_summary()

    assert result["ok"] is False
    assert "does not expose PCB editor document APIs" in str(result["message"])


async def test_set_visible_layers_requires_mutation_gate() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_visible_layers(["F.Cu", "Edge.Cuts"])

    assert result["ok"] is False
    assert "KIPILOT_ENABLE_MUTATIONS=1" in str(result["message"])


async def test_set_visible_layers_dry_run_works_without_mutation_gate() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_visible_layers(["F.Cu", "Edge.Cuts"], dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "set_visible_layers",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "previous_visible_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 31, "name": "B.Cu"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
        "visible_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
        "requested_layers": ["F.Cu", "Edge.Cuts"],
        "resolved_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_set_visible_layers_commits_when_enabled() -> None:
    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=True, commit_message_prefix="Custom Prefix"),
        kicad_factory=FakeMutationKiCad,
    )

    result = await client.set_visible_layers(["F.Cu", "Edge.Cuts"])

    assert result["ok"] is True
    assert result["mutation"] == "set_visible_layers"
    assert result["dry_run"] is False
    assert result["commit_message"] == "Custom Prefix: set_visible_layers"
    assert result["visible_layers"] == [
        {"id": 0, "name": "F.Cu"},
        {"id": 44, "name": "Edge.Cuts"},
    ]
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("set_visible_layers", [0, 44]),
        ("push_commit", "fake-commit", "Custom Prefix: set_visible_layers"),
    ]


async def test_set_active_layer_dry_run_previews_target_layer() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_active_layer("F.SilkS", dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "set_active_layer",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "previous_active_layer": {"id": 0, "name": "F.Cu"},
        "active_layer": {"id": 37, "name": "F.SilkS"},
        "requested_layer": "F.SilkS",
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_set_active_layer_commits_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_active_layer("F.SilkS")

    assert result["ok"] is True
    assert result["mutation"] == "set_active_layer"
    assert result["active_layer"] == {"id": 37, "name": "F.SilkS"}
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("set_active_layer", 37),
        ("push_commit", "fake-commit", "KiPilot MCP: set_active_layer"),
    ]


async def test_set_enabled_layers_dry_run_previews_target_non_copper_layers() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_enabled_layers(["F.SilkS", "Edge.Cuts"], dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "set_enabled_layers",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "dangerous": True,
        "copper_layer_count": 2,
        "previous_enabled_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 31, "name": "B.Cu"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
        "enabled_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 31, "name": "B.Cu"},
            {"id": 37, "name": "F.SilkS"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
        "requested_non_copper_layers": ["F.SilkS", "Edge.Cuts"],
        "resolved_non_copper_layers": [
            {"id": 37, "name": "F.SilkS"},
            {"id": 44, "name": "Edge.Cuts"},
        ],
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_set_enabled_layers_requires_force_for_live_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_enabled_layers(["F.SilkS", "Edge.Cuts"])

    assert result["ok"] is False
    assert "force=True" in str(result["message"])


async def test_set_enabled_layers_commits_when_forced() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_enabled_layers(["F.SilkS", "Edge.Cuts"], force=True)

    assert result["ok"] is True
    assert result["mutation"] == "set_enabled_layers"
    assert result["enabled_layers"] == [
        {"id": 0, "name": "F.Cu"},
        {"id": 31, "name": "B.Cu"},
        {"id": 37, "name": "F.SilkS"},
        {"id": 44, "name": "Edge.Cuts"},
    ]
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("set_enabled_layers", 2, [37, 44]),
        ("push_commit", "fake-commit", "KiPilot MCP: set_enabled_layers"),
    ]


async def test_revert_board_requires_force_guard() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.revert_board()

    assert result["ok"] is False
    assert "force=True" in str(result["message"])


async def test_revert_board_dry_run_reports_action_without_force() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.revert_board(dry_run=True, force=True)

    assert result == {
        "ok": True,
        "mutation": "revert_board",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "dangerous": True,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_revert_board_executes_when_enabled_and_forced() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.revert_board(force=True)

    assert result == {
        "ok": True,
        "mutation": "revert_board",
        "dry_run": False,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "dangerous": True,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("revert",),
    ]


async def test_revert_board_retries_timeout_once_and_succeeds() -> None:
    FlakyRevertMutationBoard.remaining_revert_failures = 1
    FlakyRevertKiCad.instances = []

    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FlakyRevertKiCad)

    result = await client.revert_board(force=True)

    assert result["ok"] is True
    assert result["mutation"] == "revert_board"
    assert len(FlakyRevertKiCad.instances) == 2
    assert FlakyRevertKiCad.instances[0].board.calls == [
        ("revert",),
    ]
    assert FlakyRevertKiCad.instances[1].board.calls == [
        ("revert",),
    ]


async def test_move_footprint_requires_reference_or_id() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.move_footprint(x_mm=2.0, y_mm=3.0, dry_run=True)

    assert result["ok"] is False
    assert result["message"] == "Footprint lookup requires either reference or footprint_id."


async def test_move_footprint_dry_run_previews_updated_position() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.move_footprint(reference="R1", x_mm=2.0, y_mm=3.0, dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "move_footprint",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "target": {
            "reference": "R1",
            "footprint_id": None,
        },
        "previous_footprint": {
            "id": "footprint-id",
            "reference": "R1",
            "value": "10k",
            "position": {
                "x_nm": 1_500_000,
                "y_nm": 2_500_000,
                "x_mm": 1.5,
                "y_mm": 2.5,
            },
            "orientation": "90deg",
            "layer": 0,
            "locked": False,
        },
        "footprint": {
            "id": "footprint-id",
            "reference": "R1",
            "value": "10k",
            "position": {
                "x_nm": 2_000_000,
                "y_nm": 3_000_000,
                "x_mm": 2.0,
                "y_mm": 3.0,
            },
            "orientation": "90deg",
            "layer": 0,
            "locked": False,
        },
        "requested_position": {
            "x_nm": 2_000_000,
            "y_nm": 3_000_000,
            "x_mm": 2.0,
            "y_mm": 3.0,
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_move_footprint_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.move_footprint(footprint_id="footprint-id", x_mm=2.0, y_mm=3.0)

    assert result["ok"] is True
    assert result["mutation"] == "move_footprint"
    assert result["dry_run"] is False
    assert result["commit_message"] == "KiPilot MCP: move_footprint"
    assert result["footprint"]["position"] == {
        "x_nm": 2_000_000,
        "y_nm": 3_000_000,
        "x_mm": 2.0,
        "y_mm": 3.0,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["footprint-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: move_footprint"),
    ]


async def test_rotate_footprint_dry_run_previews_updated_orientation() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.rotate_footprint(reference="R1", orientation_degrees=45, dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "rotate_footprint",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "target": {
            "reference": "R1",
            "footprint_id": None,
        },
        "previous_footprint": {
            "id": "footprint-id",
            "reference": "R1",
            "value": "10k",
            "position": {
                "x_nm": 1_500_000,
                "y_nm": 2_500_000,
                "x_mm": 1.5,
                "y_mm": 2.5,
            },
            "orientation": "90deg",
            "layer": 0,
            "locked": False,
        },
        "footprint": {
            "id": "footprint-id",
            "reference": "R1",
            "value": "10k",
            "position": {
                "x_nm": 1_500_000,
                "y_nm": 2_500_000,
                "x_mm": 1.5,
                "y_mm": 2.5,
            },
            "orientation": "45deg",
            "layer": 0,
            "locked": False,
        },
        "requested_orientation_degrees": 45.0,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_rotate_footprint_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.rotate_footprint(footprint_id="footprint-id", orientation_degrees=45)

    assert result["ok"] is True
    assert result["mutation"] == "rotate_footprint"
    assert result["dry_run"] is False
    assert result["commit_message"] == "KiPilot MCP: rotate_footprint"
    assert result["footprint"]["orientation"] == "45deg"
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["footprint-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: rotate_footprint"),
    ]


async def test_set_board_origin_dry_run_previews_target_origin() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_board_origin(origin_type="grid", x_mm=1.25, y_mm=2.5, dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "set_board_origin",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "origin_type": {"id": 1, "name": "grid"},
        "previous_origin": {
            "x_nm": 0,
            "y_nm": 0,
            "x_mm": 0.0,
            "y_mm": 0.0,
        },
        "origin": {
            "x_nm": 1_250_000,
            "y_nm": 2_500_000,
            "x_mm": 1.25,
            "y_mm": 2.5,
        },
        "requested_origin": {
            "x_nm": 1_250_000,
            "y_nm": 2_500_000,
            "x_mm": 1.25,
            "y_mm": 2.5,
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_set_board_origin_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_board_origin(origin_type="drill", x_mm=10.0, y_mm=11.0)

    assert result["ok"] is True
    assert result["mutation"] == "set_board_origin"
    assert result["origin_type"] == {"id": 2, "name": "drill"}
    assert result["origin"] == {
        "x_nm": 10_000_000,
        "y_nm": 11_000_000,
        "x_mm": 10.0,
        "y_mm": 11.0,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("set_origin", 2, 10_000_000, 11_000_000),
        ("push_commit", "fake-commit", "KiPilot MCP: set_board_origin"),
    ]


async def test_set_title_block_requires_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_title_block(dry_run=True)

    assert result["ok"] is False
    assert result["message"] == "At least one title block field or comment must be provided."


async def test_set_title_block_dry_run_previews_merged_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_title_block(
        title="Updated Board",
        comments={2: "Released", "3": "Customer"},
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "set_title_block",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "previous_title_block": {
            "title": "Demo Board",
            "revision": "A",
            "date": "2026-05-09",
            "company": "KiPilot Labs",
            "comments": {
                "1": "Prototype",
                "2": "Internal",
            },
        },
        "title_block": {
            "title": "Updated Board",
            "revision": "A",
            "date": "2026-05-09",
            "company": "KiPilot Labs",
            "comments": {
                "1": "Prototype",
                "2": "Released",
                "3": "Customer",
            },
        },
        "requested_changes": {
            "title": "Updated Board",
            "revision": None,
            "date": None,
            "company": None,
            "comments": {
                "2": "Released",
                "3": "Customer",
            },
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_set_title_block_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_title_block(revision="B", company="KiPilot Systems")

    assert result["ok"] is True
    assert result["mutation"] == "set_title_block"
    assert result["title_block"] == {
        "title": "Demo Board",
        "revision": "B",
        "date": "2026-05-09",
        "company": "KiPilot Systems",
        "comments": {
            "1": "Prototype",
            "2": "Internal",
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        (
            "set_title_block_info",
            "Demo Board",
            "B",
            "2026-05-09",
            "KiPilot Systems",
            {1: "Prototype", 2: "Internal"},
        ),
        ("push_commit", "fake-commit", "KiPilot MCP: set_title_block"),
    ]


async def test_update_board_text_dry_run_previews_text_change() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.update_board_text(
        text_id="board-text-id",
        new_text="Mainboard v1.2",
        expected_current_text="Mainboard v1.1",
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "update_board_text",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "target": {"text_id": "board-text-id"},
        "previous_text_item": {
            "id": "board-text-id",
            "kind": "FakeMutableBoardText",
            "text": "Mainboard v1.1",
            "layer": {"id": 37, "name": "F.SilkS"},
            "locked": False,
            "position": {
                "x_nm": 20_000_000,
                "y_nm": 10_000_000,
                "x_mm": 20.0,
                "y_mm": 10.0,
            },
        },
        "text_item": {
            "id": "board-text-id",
            "kind": "FakeMutableBoardText",
            "text": "Mainboard v1.2",
            "layer": {"id": 37, "name": "F.SilkS"},
            "locked": False,
            "position": {
                "x_nm": 20_000_000,
                "y_nm": 10_000_000,
                "x_mm": 20.0,
                "y_mm": 10.0,
            },
        },
        "requested_changes": {
            "new_text": "Mainboard v1.2",
            "expected_current_text": "Mainboard v1.1",
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_update_board_text_rejects_stale_expected_value() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.update_board_text(
        text_id="board-text-id",
        new_text="Mainboard v1.2",
        expected_current_text="Wrong Value",
        dry_run=True,
    )

    assert result["ok"] is False
    assert "did not match expected text" in str(result["message"])


async def test_update_board_text_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.update_board_text(
        text_id="board-text-id",
        new_text="Mainboard v1.2",
        expected_current_text="Mainboard v1.1",
    )

    assert result["ok"] is True
    assert result["mutation"] == "update_board_text"
    assert result["text_item"]["text"] == "Mainboard v1.2"
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["board-text-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: update_board_text"),
    ]


async def test_create_track_segments_dry_run_previews_tracks() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.create_track_segments(
        points=[
            {"x_mm": 1.0, "y_mm": 2.0},
            {"x_mm": 3.0, "y_mm": 2.0},
            {"x_mm": 3.0, "y_mm": 4.0},
        ],
        layer="F.Cu",
        width_mm=0.25,
        net_name="+3V3",
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["mutation"] == "create_track_segments"
    assert result["count"] == 2
    assert result["layer"] == {"id": 0, "name": "F.Cu"}
    assert result["net"] == {"name": "+3V3", "code": 7}
    assert result["tracks"][0]["start"] == {
        "x_nm": 1_000_000,
        "y_nm": 2_000_000,
        "x_mm": 1.0,
        "y_mm": 2.0,
    }
    assert result["tracks"][1]["end"] == {
        "x_nm": 3_000_000,
        "y_nm": 4_000_000,
        "x_mm": 3.0,
        "y_mm": 4.0,
    }
    assert result["tracks"][0]["width_mm"] == 0.25
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_create_track_segments_creates_items_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.create_track_segments(
        points=[
            {"x_mm": 0.0, "y_mm": 0.0},
            {"x_mm": 10.0, "y_mm": 0.0},
        ],
        layer=0,
        width_mm=0.2,
    )

    assert result["ok"] is True
    assert result["tracks"][0]["id"] == "track-created-1"
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("create_items", ["track-created-1"]),
        ("push_commit", "fake-commit", "KiPilot MCP: create_track_segments"),
    ]


async def test_create_via_dry_run_previews_via() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.create_via(
        x_mm=5.0,
        y_mm=6.0,
        diameter_mm=0.7,
        drill_diameter_mm=0.3,
        net_name="GND",
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["mutation"] == "create_via"
    assert result["via_type"] == {"id": 1, "name": "through"}
    assert result["via"]["position"] == {
        "x_nm": 5_000_000,
        "y_nm": 6_000_000,
        "x_mm": 5.0,
        "y_mm": 6.0,
    }
    assert result["via"]["diameter_mm"] == 0.7
    assert result["via"]["drill_diameter_mm"] == 0.3
    assert result["via"]["net"] == {"name": "GND", "code": 1}
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_update_items_dry_run_previews_whitelisted_updates() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.update_items(
        updates=[
            {
                "kind": "footprint",
                "reference": "R1",
                "x_mm": 2.0,
                "y_mm": 3.0,
                "orientation_degrees": 45,
            },
            {
                "kind": "track",
                "track_id": "track-id",
                "end_x_mm": 8.0,
                "end_y_mm": 2.5,
                "width_mm": 0.3,
            },
            {
                "kind": "zone",
                "zone_id": "zone-id",
                "outline_points": [
                    {"x_mm": 0.0, "y_mm": 0.0},
                    {"x_mm": 12.0, "y_mm": 0.0},
                    {"x_mm": 12.0, "y_mm": 6.0},
                    {"x_mm": 0.0, "y_mm": 6.0},
                ],
            },
        ],
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["mutation"] == "update_items"
    assert result["count"] == 3
    assert result["allowed_kinds"] == ["footprint", "track", "zone"]
    assert result["updates"][0]["item"]["position"] == {
        "x_nm": 2_000_000,
        "y_nm": 3_000_000,
        "x_mm": 2.0,
        "y_mm": 3.0,
    }
    assert result["updates"][0]["item"]["orientation"] == "45deg"
    assert result["updates"][1]["item"]["end"] == {
        "x_nm": 8_000_000,
        "y_nm": 2_500_000,
        "x_mm": 8.0,
        "y_mm": 2.5,
    }
    assert result["updates"][1]["item"]["width_mm"] == 0.3
    assert result["updates"][2]["item"]["outline"]["outline"][1]["x_mm"] == 12.0
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_update_items_updates_multiple_items_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.update_items(
        updates=[
            {
                "kind": "footprint",
                "footprint_id": "footprint-id",
                "orientation_degrees": 45,
            },
            {
                "kind": "track",
                "track_id": "track-id",
                "locked": True,
            },
        ]
    )

    assert result["ok"] is True
    assert result["mutation"] == "update_items"
    assert result["updates"][0]["item"]["orientation"] == "45deg"
    assert result["updates"][1]["item"]["locked"] is True
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["footprint-id", "track-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: update_items"),
    ]


async def test_update_items_rejects_unsupported_fields() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.update_items(
        updates=[
            {
                "kind": "track",
                "track_id": "track-id",
                "diameter_mm": 0.5,
            }
        ],
        dry_run=True,
    )

    assert result["ok"] is False
    assert "unsupported fields" in str(result["message"])


async def test_update_track_geometry_dry_run_previews_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.update_track_geometry(
        track_id="track-id",
        end_x_mm=8.0,
        end_y_mm=2.5,
        width_mm=0.3,
        layer="B.Cu",
        locked=True,
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["mutation"] == "update_track_geometry"
    assert result["track"]["end"] == {
        "x_nm": 8_000_000,
        "y_nm": 2_500_000,
        "x_mm": 8.0,
        "y_mm": 2.5,
    }
    assert result["track"]["width_mm"] == 0.3
    assert result["track"]["layer"] == {"id": 31, "name": "B.Cu"}
    assert result["track"]["locked"] is True
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_update_zone_outline_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.update_zone_outline(
        zone_id="zone-id",
        outline_points=[
            {"x_mm": 0.0, "y_mm": 0.0},
            {"x_mm": 12.0, "y_mm": 0.0},
            {"x_mm": 12.0, "y_mm": 6.0},
            {"x_mm": 0.0, "y_mm": 6.0},
        ],
    )

    assert result["ok"] is True
    assert result["mutation"] == "update_zone_outline"
    assert result["zone"]["outline"]["outline"][1]["x_mm"] == 12.0
    assert result["zone"]["outline"]["outline"][2]["y_mm"] == 6.0
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["zone-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: update_zone_outline"),
    ]


async def test_delete_items_requires_force_guard() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.delete_items(item_ids=["track-id"])

    assert result["ok"] is False
    assert "force=True" in str(result["message"])


async def test_delete_items_dry_run_previews_targets() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.delete_items(item_ids=["track-id", "via-id"], dry_run=True, force=True)

    assert result["ok"] is True
    assert result["mutation"] == "delete_items"
    assert result["dangerous"] is True
    assert result["item_ids"] == ["track-id", "via-id"]
    assert [item["id"] for item in result["items"]] == ["track-id", "via-id"]
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_delete_items_removes_targets_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.delete_items(item_ids=["track-id"], force=True)

    assert result["ok"] is True
    assert result["count"] == 1
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("remove_items", ["track-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: delete_items"),
    ]
    assert FakeMutationKiCad.last_instance.board.get_tracks() == []


async def test_refill_zones_dry_run_previews_selected_zones() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.refill_zones(zone_ids=["zone-id"], dry_run=True)

    assert result["ok"] is True
    assert result["mutation"] == "refill_zones"
    assert result["count"] == 1
    assert result["zone_ids"] == ["zone-id"]
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_refill_zones_executes_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.refill_zones(zone_ids=["zone-id"])

    assert result["ok"] is True
    assert result["count"] == 1
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("refill_zones", ["zone-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: refill_zones"),
    ]


async def test_refill_zones_retries_busy_once_and_succeeds() -> None:
    FlakyRefillMutationBoard.remaining_refill_failures = 1
    FlakyRefillKiCad.instances = []

    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FlakyRefillKiCad)

    result = await client.refill_zones(zone_ids=["zone-id"])

    assert result["ok"] is True
    assert result["mutation"] == "refill_zones"
    assert len(FlakyRefillKiCad.instances) == 2
    assert FlakyRefillKiCad.instances[0].board.calls == [
        ("begin_commit",),
        ("refill_zones", ["zone-id"]),
        ("drop_commit", "fake-commit"),
    ]
    assert FlakyRefillKiCad.instances[1].board.calls == [
        ("begin_commit",),
        ("refill_zones", ["zone-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: refill_zones"),
    ]


async def test_save_board_dry_run_previews_target_file() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.save_board(dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "save_board",
        "dry_run": True,
        "commit_message": None,
        "board": {
            "name": "demo.kicad_pcb",
            "document": {
                "type": "1",
                "board_filename": "demo.kicad_pcb",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            },
        },
        "saved_filename": "demo.kicad_pcb",
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_save_board_executes_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.save_board()

    assert result["ok"] is True
    assert result["saved_filename"] == "demo.kicad_pcb"
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [("save",)]


class FakeBoardKiCad:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def get_board(self) -> FakeBoard:
        return FakeBoard()

    def close(self) -> None:
        pass


class FakeMutationKiCad(FakeBoardKiCad):
    last_instance: FakeMutationKiCad | None = None

    def __init__(self, **_kwargs: object) -> None:
        self.board = FakeMutationBoard()
        FakeMutationKiCad.last_instance = self

    def get_board(self) -> FakeMutationBoard:
        return self.board


class FlakyRevertKiCad(FakeBoardKiCad):
    instances: list[FlakyRevertKiCad] = []

    def __init__(self, **_kwargs: object) -> None:
        self.board = FlakyRevertMutationBoard()
        type(self).instances.append(self)

    def get_board(self) -> FlakyRevertMutationBoard:
        return self.board


class FlakyRefillKiCad(FakeBoardKiCad):
    instances: list[FlakyRefillKiCad] = []

    def __init__(self, **_kwargs: object) -> None:
        self.board = FlakyRefillMutationBoard()
        type(self).instances.append(self)

    def get_board(self) -> FlakyRefillMutationBoard:
        return self.board


class FakeBoard:
    name = "demo.kicad_pcb"
    document = type(
        "FakeDocument",
        (),
        {
            "type": 1,
            "board_filename": "demo.kicad_pcb",
            "project": type(
                "FakeProjectRef",
                (),
                {"name": "demo", "path": "C:/demo/demo.kicad_pro"},
            )(),
        },
    )()

    def get_project(self) -> FakeProject:
        return FakeProject()

    def get_footprints(self) -> list[FakeFootprint]:
        return [FakeFootprint(), FakeFootprintB()]

    def get_nets(self) -> list[FakeNet]:
        return [FakeNet(), FakeGroundNet()]

    def get_tracks(self) -> list[FakeTrack]:
        return [FakeTrack()]

    def get_vias(self) -> list[FakeVia]:
        return [FakeVia()]

    def get_zones(self) -> list[FakeZone]:
        return [FakeZone()]

    def get_shapes(self) -> list[FakeShape]:
        return [
            FakeShape("shape-edge-1", 44, FakeVector(0, 0), FakeVector(10_000_000, 0)),
            FakeShape(
                "shape-silk-1",
                37,
                FakeVector(1_000_000, 1_000_000),
                FakeVector(2_000_000, 2_000_000),
            ),
        ]

    def get_text(self) -> list[object]:
        return [
            FakeMutableBoardText(
                text_id="board-text-id",
                value="Mainboard v1.1",
                layer=37,
                position=FakeVector(20_000_000, 10_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-2",
                value="REV A",
                layer=37,
                position=FakeVector(8_000_000, 7_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-3",
                value="SN: 0001",
                layer=37,
                position=FakeVector(8_000_000, 9_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-4",
                value="www.example.com",
                layer=37,
                position=FakeVector(25_000_000, 16_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-5",
                value="TOP",
                layer=37,
                position=FakeVector(2_000_000, 2_000_000),
            ),
            FakeMutableBoardTextBox(
                text_id="board-textbox-id",
                value="Assembly notes",
                layer=37,
                top_left=FakeVector(30_000_000, 5_000_000),
                bottom_right=FakeVector(40_000_000, 12_000_000),
            ),
        ]

    def get_pads(self) -> list[FakePad]:
        return [FakePad()]

    def get_copper_layer_count(self) -> int:
        return 2

    def get_active_layer(self) -> int:
        return 0

    def get_visible_layers(self) -> list[int]:
        return [0, 31, 44]

    def get_enabled_layers(self) -> list[int]:
        return [0, 31, 44]

    def get_layer_name(self, layer: int) -> str:
        names = {
            0: "F.Cu",
            31: "B.Cu",
            36: "B.SilkS",
            37: "F.SilkS",
            44: "Edge.Cuts",
        }
        return names.get(layer, "")

    def get_stackup(self) -> FakeStackup:
        return FakeStackup()

    def get_origin(self, origin_type: int) -> FakeVector:
        origins = {
            1: FakeVector(0, 0),
            2: FakeVector(59_900_000, 138_400_000),
        }
        return origins[origin_type]

    def get_title_block_info(self) -> FakeTitleBlock:
        return FakeTitleBlock(
            title="Demo Board",
            revision="A",
            date="2026-05-09",
            company="KiPilot Labs",
            comments={1: "Prototype", 2: "Internal"},
        )

    def get_items_by_net(self, _net: object, types: object | None = None) -> list[object]:
        _ = types
        return [FakeTrack(), FakeVia(), FakePad()]

    def get_items_by_netclass(
        self, net_classes: str | list[str], types: object | None = None
    ) -> list[object]:
        _ = types
        names = net_classes if isinstance(net_classes, list) else [net_classes]
        normalized_names = {str(name).strip().lower() for name in names}
        if "power" in normalized_names:
            return [FakeTrack(), FakeVia(), FakePad()]
        if "default" in normalized_names:
            return [FakeZone()]
        return []

    def get_netclass_for_nets(self, nets: object | list[object]) -> dict[str, FakeNetClass]:
        resolved_nets = nets if isinstance(nets, list) else [nets]
        result: dict[str, FakeNetClass] = {}
        for net in resolved_nets:
            net_name = str(getattr(net, "name", ""))
            if net_name == "+3V3":
                result[net_name] = FakeNetClass(
                    name="Power",
                    description="Power distribution",
                    clearance=300_000,
                    track_width=500_000,
                    via_diameter=800_000,
                    via_drill=400_000,
                )
            elif net_name == "GND":
                result[net_name] = FakeNetClass(
                    name="Default",
                    description="Default routing rules",
                    clearance=200_000,
                    track_width=250_000,
                    via_diameter=600_000,
                    via_drill=300_000,
                )
        return result

    def get_connected_items(
        self, items: object | list[object], types: object | None = None
    ) -> list[object]:
        _ = types
        resolved_items = items if isinstance(items, list) else [items]
        item_ids = {str(getattr(item, "id", item)) for item in resolved_items}
        if "track-id" in item_ids:
            return [FakeTrack(), FakeVia(), FakePad()]
        if "pad-id" in item_ids:
            return [FakeTrack(), FakeVia()]
        return []

    def get_item_bounding_box(self, item: object, include_text: bool = False) -> FakeBox | None:
        _ = include_text
        if isinstance(item, FakeFootprint):
            return FakeBox(FakeVector(1_250_000, 2_250_000), FakeVector(1_750_000, 2_750_000))
        if isinstance(item, FakeFootprintB):
            return FakeBox(FakeVector(4_250_000, 750_000), FakeVector(4_750_000, 1_250_000))
        if hasattr(item, "bounding_box"):
            return item.bounding_box()
        position = getattr(item, "position", None)
        if position is None:
            return None
        return FakeBox(position, position)


class FakeFootprint:
    id = "footprint-id"
    reference_field = type(
        "FakeReferenceField",
        (),
        {"text": type("FakeReferenceText", (), {"value": "R1"})()},
    )()
    value_field = type(
        "FakeValueField",
        (),
        {"text": type("FakeValueText", (), {"value": "10k"})()},
    )()
    position = type("FakePosition", (), {"x": 1_500_000, "y": 2_500_000})()
    orientation = "90deg"
    layer = 0
    locked = False


class FakeFootprintB:
    id = "footprint-b-id"
    reference_field = type(
        "FakeReferenceFieldB",
        (),
        {"text": type("FakeReferenceTextB", (), {"value": "C5"})()},
    )()
    value_field = type(
        "FakeValueFieldB",
        (),
        {"text": type("FakeValueTextB", (), {"value": "100n"})()},
    )()
    position = type("FakePositionB", (), {"x": 4_500_000, "y": 1_000_000})()
    orientation = "0deg"
    layer = 31
    locked = False


class FakeNet:
    name = "+3V3"
    code = 7


class FakeGroundNet:
    name = "GND"
    code = 1


class FakeProject:
    name = "demo"
    path = "C:/demo/demo.kicad_pro"
    document = type(
        "FakeProjectDocument",
        (),
        {
            "type": 2,
            "board_filename": "",
            "path": "C:/demo/demo.kicad_pro",
            "project": type(
                "FakeProjectDocumentProject",
                (),
                {"name": "demo", "path": "C:/demo/demo.kicad_pro"},
            )(),
        },
    )()

    def get_text_variables(self) -> dict[str, str]:
        return {
            "BOARD_REV": "A",
            "AUTHOR": "KiPilot",
        }

    def expand_text_variables(self, text: str) -> str:
        return text.replace("${BOARD_REV}", "A").replace("${AUTHOR}", "KiPilot")

    def get_net_classes(self) -> list[FakeNetClass]:
        return [
            FakeNetClass(
                name="Default",
                description="Default routing rules",
                clearance=200_000,
                track_width=250_000,
                via_diameter=600_000,
                via_drill=300_000,
            ),
            FakeNetClass(
                name="Power",
                description="Power distribution",
                clearance=300_000,
                track_width=500_000,
                via_diameter=800_000,
                via_drill=400_000,
            ),
        ]


class FakeStackup:
    layers = [
        type(
            "FakeStackupLayerCopper",
            (),
            {
                "layer": 0,
                "user_name": "F.Cu",
                "enabled": True,
                "type": "copper",
                "material_name": "Copper",
                "thickness": 35_000,
                "dielectric": None,
            },
        )(),
        type(
            "FakeStackupLayerDielectric",
            (),
            {
                "layer": -1,
                "user_name": "Core",
                "enabled": True,
                "type": "dielectric",
                "material_name": "FR4",
                "thickness": 800_000,
                "dielectric": type(
                    "FakeDielectric",
                    (),
                    {
                        "layers": [
                            type(
                                "FakeDielectricLayer",
                                (),
                                {
                                    "material_name": "FR4",
                                    "epsilon_r": 4.2,
                                    "loss_tangent": 0.02,
                                    "thickness": 800_000,
                                },
                            )()
                        ]
                    },
                )(),
            },
        )(),
    ]


class FakeVector:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class FakeNetClass:
    def __init__(
        self,
        *,
        name: str,
        description: str,
        clearance: int,
        track_width: int,
        via_diameter: int,
        via_drill: int,
    ) -> None:
        self.name = name
        self.description = description
        self.clearance = clearance
        self.track_width = track_width
        self.via_diameter = via_diameter
        self.via_drill = via_drill


class FakeAngle:
    def __init__(self, degrees: float) -> None:
        self.degrees = float(degrees)

    @classmethod
    def from_degrees(cls, degrees: float) -> FakeAngle:
        return cls(degrees)

    def normalize(self) -> FakeAngle:
        return type(self)(self.degrees % 360)

    def __str__(self) -> str:
        if self.degrees.is_integer():
            return f"{int(self.degrees)}deg"
        return f"{self.degrees}deg"


class FakeTitleBlock:
    def __init__(
        self,
        proto: FakeTitleBlock | None = None,
        *,
        title: str = "",
        revision: str = "",
        date: str = "",
        company: str = "",
        comments: dict[int, str] | None = None,
    ) -> None:
        if proto is not None:
            title = proto.title
            revision = proto.revision
            date = proto.date
            company = proto.company
            comments = dict(proto.comments)

        self.title = title
        self.revision = revision
        self.date = date
        self.company = company
        self.comments = dict(comments or {})
        self.proto = self


class FakeBox:
    def __init__(self, top_left: FakeVector, bottom_right: FakeVector) -> None:
        self.top_left = top_left
        self.bottom_right = bottom_right


class FakeTrack:
    id = "track-id"
    start = FakeVector(1_000_000, 2_000_000)
    end = FakeVector(6_000_000, 2_000_000)
    layer = 0
    net = FakeNet()
    locked = False
    width = 250_000

    def length(self) -> float:
        return 5_000_000.0

    def bounding_box(self) -> FakeBox:
        return FakeBox(self.start, self.end)


class FakeViaPadStack:
    layers = [0, 31]


class FakeVia:
    id = "via-id"
    position = FakeVector(3_000_000, 3_500_000)
    net = FakeNet()
    locked = False
    diameter = 600_000
    drill_diameter = 300_000
    type = "through"
    padstack = FakeViaPadStack()


class FakePolygon:
    outline = [
        FakeVector(0, 0),
        FakeVector(10_000_000, 0),
        FakeVector(10_000_000, 8_000_000),
        FakeVector(0, 8_000_000),
    ]


class FakeZone:
    id = "zone-id"
    name = "Power Pour"
    net = FakeGroundNet()
    layers = [0, 31]
    locked = False
    filled = True
    priority = 2
    type = "copper"
    outline = FakePolygon()

    def bounding_box(self) -> FakeBox:
        return FakeBox(FakeVector(0, 0), FakeVector(10_000_000, 8_000_000))


class FakePadStack:
    layers = [0]


class FakePad:
    id = "pad-id"
    number = "1"
    position = FakeVector(2_000_000, 4_000_000)
    net = FakeNet()
    pad_type = "smd"
    padstack = FakePadStack()


class FakeShape:
    def __init__(self, shape_id: str, layer: int, start: FakeVector, end: FakeVector) -> None:
        self.id = shape_id
        self.layer = layer
        self.start = start
        self.end = end
        self.locked = False
        self.net = None

    def bounding_box(self) -> FakeBox:
        return FakeBox(self.start, self.end)


class FakeMutationBoard(FakeBoard):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._next_created_item_id = 1
        self._active_layer = 0
        self._visible_layers = [0, 31, 44]
        self._enabled_layers = [0, 31, 44]
        self._origins = {
            1: FakeVector(0, 0),
            2: FakeVector(59_900_000, 138_400_000),
        }
        self._title_block = FakeTitleBlock(
            title="Demo Board",
            revision="A",
            date="2026-05-09",
            company="KiPilot Labs",
            comments={1: "Prototype", 2: "Internal"},
        )
        self._footprints = [
            FakeMutableFootprint(
                footprint_id="footprint-id",
                reference="R1",
                value="10k",
                position=FakeVector(1_500_000, 2_500_000),
                orientation=FakeAngle(90),
                layer=0,
            ),
            FakeMutableFootprint(
                footprint_id="footprint-b-id",
                reference="C5",
                value="100n",
                position=FakeVector(4_500_000, 1_000_000),
                orientation=FakeAngle(0),
                layer=31,
            ),
        ]
        self._tracks = [
            FakeMutableTrack(
                track_id="track-id",
                start=FakeVector(1_000_000, 2_000_000),
                end=FakeVector(6_000_000, 2_000_000),
                layer=0,
                width=250_000,
                net=FakeNet(),
            )
        ]
        self._vias = [
            FakeMutableVia(
                via_id="via-id",
                position=FakeVector(3_000_000, 3_500_000),
                net=FakeNet(),
                diameter=600_000,
                drill_diameter=300_000,
                via_type=1,
            )
        ]
        self._zones = [
            FakeMutableZone(
                zone_id="zone-id",
                name="Power Pour",
                net=FakeGroundNet(),
                layers=[0, 31],
                priority=2,
                outline=FakeMutablePolygon(
                    outline=[
                        FakeVector(0, 0),
                        FakeVector(10_000_000, 0),
                        FakeVector(10_000_000, 8_000_000),
                        FakeVector(0, 8_000_000),
                    ]
                ),
            )
        ]
        self._text_items = [
            FakeMutableBoardText(
                text_id="board-text-id",
                value="Mainboard v1.1",
                layer=37,
                position=FakeVector(20_000_000, 10_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-2",
                value="REV A",
                layer=37,
                position=FakeVector(8_000_000, 7_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-3",
                value="SN: 0001",
                layer=37,
                position=FakeVector(8_000_000, 9_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-4",
                value="www.example.com",
                layer=37,
                position=FakeVector(25_000_000, 16_000_000),
            ),
            FakeMutableBoardText(
                text_id="board-text-5",
                value="TOP",
                layer=37,
                position=FakeVector(2_000_000, 2_000_000),
            ),
            FakeMutableBoardTextBox(
                text_id="board-textbox-id",
                value="Assembly notes",
                layer=37,
                top_left=FakeVector(30_000_000, 5_000_000),
                bottom_right=FakeVector(40_000_000, 12_000_000),
            ),
        ]

    def get_footprints(self) -> list[FakeMutableFootprint]:
        return list(self._footprints)

    def get_tracks(self) -> list[FakeMutableTrack]:
        return list(self._tracks)

    def get_vias(self) -> list[FakeMutableVia]:
        return list(self._vias)

    def get_zones(self) -> list[FakeMutableZone]:
        return list(self._zones)

    def get_text(self) -> list[object]:
        return list(self._text_items)

    def get_origin(self, origin_type: int) -> FakeVector:
        return self._origins[origin_type]

    def get_title_block_info(self) -> FakeTitleBlock:
        return FakeTitleBlock(self._title_block)

    def get_active_layer(self) -> int:
        return self._active_layer

    def get_visible_layers(self) -> list[int]:
        return list(self._visible_layers)

    def get_enabled_layers(self) -> list[int]:
        return list(self._enabled_layers)

    def begin_commit(self) -> str:
        self.calls.append(("begin_commit",))
        return "fake-commit"

    def push_commit(self, commit: str, message: str = "") -> None:
        self.calls.append(("push_commit", commit, message))

    def drop_commit(self, commit: str) -> None:
        self.calls.append(("drop_commit", commit))

    def set_visible_layers(self, layers: list[int]) -> None:
        self.calls.append(("set_visible_layers", list(layers)))
        self._visible_layers = list(layers)

    def set_active_layer(self, layer: int) -> None:
        self.calls.append(("set_active_layer", layer))
        self._active_layer = layer

    def set_enabled_layers(self, copper_layer_count: int, layers: list[int]) -> list[int]:
        self.calls.append(("set_enabled_layers", copper_layer_count, list(layers)))
        self._enabled_layers = [0, 31, *list(layers)]
        return list(self._enabled_layers)

    def revert(self) -> None:
        self.calls.append(("revert",))

    def set_origin(self, origin_type: int, origin: FakeVector) -> None:
        self.calls.append(("set_origin", origin_type, origin.x, origin.y))
        self._origins[origin_type] = FakeVector(origin.x, origin.y)

    def set_title_block_info(self, title_block: FakeTitleBlock) -> None:
        self.calls.append(
            (
                "set_title_block_info",
                title_block.title,
                title_block.revision,
                title_block.date,
                title_block.company,
                dict(title_block.comments),
            )
        )
        self._title_block = FakeTitleBlock(title_block)

    def update_items(self, items: object | list[object]) -> list[object]:
        resolved_items = items if isinstance(items, list) else [items]
        self.calls.append(("update_items", [item.id for item in resolved_items]))

        updated: list[object] = []
        for item in resolved_items:
            replacement = self._clone_item(item)
            if self._replace_item(self._footprints, replacement):
                updated.append(replacement)
                continue
            if self._replace_item(self._tracks, replacement):
                updated.append(replacement)
                continue
            if self._replace_item(self._vias, replacement):
                updated.append(replacement)
                continue
            if self._replace_item(self._zones, replacement):
                updated.append(replacement)
                continue
            if self._replace_item(self._text_items, replacement):
                updated.append(replacement)

        return updated

    def create_items(self, items: object | list[object]) -> list[object]:
        resolved_items = items if isinstance(items, list) else [items]
        created = []

        for item in resolved_items:
            replacement = self._clone_item(item)
            if not getattr(replacement, "id", ""):
                replacement.id = self._next_item_id(replacement)
            replacement.proto = replacement

            if hasattr(replacement, "start") and hasattr(replacement, "end"):
                self._tracks.append(replacement)
            elif hasattr(replacement, "drill_diameter") and hasattr(replacement, "diameter"):
                self._vias.append(replacement)
            elif hasattr(replacement, "outline") and hasattr(replacement, "filled"):
                self._zones.append(replacement)

            created.append(replacement)

        self.calls.append(("create_items", [item.id for item in created]))
        return created

    def remove_items(self, items: object | list[object]) -> None:
        resolved_items = items if isinstance(items, list) else [items]
        item_ids = [str(getattr(item, "id", "")) for item in resolved_items]
        self.calls.append(("remove_items", item_ids))
        self._remove_item_ids(item_ids)

    def remove_items_by_id(self, item_ids: str | list[str]) -> None:
        resolved_item_ids = item_ids if isinstance(item_ids, list) else [item_ids]
        self.calls.append(("remove_items_by_id", list(resolved_item_ids)))
        self._remove_item_ids(list(resolved_item_ids))

    def refill_zones(self, zones: object | list[object] | None = None) -> list[FakeMutableZone]:
        if zones is None:
            resolved_zones = list(self._zones)
        else:
            raw_zones = zones if isinstance(zones, list) else [zones]
            zone_ids = {str(getattr(zone, "id", "")) for zone in raw_zones}
            resolved_zones = [zone for zone in self._zones if zone.id in zone_ids]

        self.calls.append(("refill_zones", [zone.id for zone in resolved_zones]))
        return list(resolved_zones)

    def save(self) -> None:
        self.calls.append(("save",))

    def _clone_item(self, item: object) -> object:
        item_type = type(item)
        proto = getattr(item, "proto", item)
        return item_type(proto)

    def _replace_item(self, items: list[object], replacement: object) -> bool:
        replacement_id = str(getattr(replacement, "id", ""))
        for index, current in enumerate(items):
            if str(getattr(current, "id", "")) == replacement_id:
                items[index] = replacement
                return True
        return False

    def _next_item_id(self, item: object) -> str:
        if hasattr(item, "start") and hasattr(item, "end"):
            prefix = "track"
        elif hasattr(item, "drill_diameter") and hasattr(item, "diameter"):
            prefix = "via"
        elif hasattr(item, "outline") and hasattr(item, "filled"):
            prefix = "zone"
        else:
            prefix = "item"

        item_id = f"{prefix}-created-{self._next_created_item_id}"
        self._next_created_item_id += 1
        return item_id

    def _remove_item_ids(self, item_ids: list[str]) -> None:
        for collection_name in ("_footprints", "_tracks", "_vias", "_zones"):
            collection = getattr(self, collection_name)
            setattr(
                self,
                collection_name,
                [item for item in collection if str(getattr(item, "id", "")) not in item_ids],
            )


class FlakyRevertMutationBoard(FakeMutationBoard):
    remaining_revert_failures = 0

    def revert(self) -> None:
        self.calls.append(("revert",))
        if type(self).remaining_revert_failures > 0:
            type(self).remaining_revert_failures -= 1
            raise ApiError("Error receiving reply from KiCad: Timed out")


class FlakyRefillMutationBoard(FakeMutationBoard):
    remaining_refill_failures = 0

    def refill_zones(self, zones: object | list[object] | None = None) -> list[FakeMutableZone]:
        result = super().refill_zones(zones)
        if type(self).remaining_refill_failures > 0:
            type(self).remaining_refill_failures -= 1
            raise ApiError(
                "KiCad returned error: KiCad is busy and cannot respond to API requests right now"
            )
        return result


class FakeMutableFootprint:
    def __init__(
        self,
        proto: FakeMutableFootprint | None = None,
        *,
        footprint_id: str = "footprint-id",
        reference: str = "R1",
        value: str = "10k",
        position: FakeVector | None = None,
        orientation: FakeAngle | None = None,
        layer: int = 0,
        locked: bool = False,
    ) -> None:
        if proto is not None:
            footprint_id = proto.id
            reference = str(proto.reference_field.text.value)
            value = str(proto.value_field.text.value)
            position = FakeVector(proto.position.x, proto.position.y)
            orientation = FakeAngle(proto.orientation.degrees)
            layer = proto.layer
            locked = proto.locked

        self.id = footprint_id
        self.reference_field = _make_fake_field(reference)
        self.value_field = _make_fake_field(value)
        self.position = position or FakeVector(0, 0)
        self.orientation = orientation or FakeAngle(0)
        self.layer = layer
        self.locked = locked
        self.proto = self


class FakeMutableTrack:
    def __init__(
        self,
        proto: FakeMutableTrack | None = None,
        *,
        track_id: str = "",
        start: FakeVector | None = None,
        end: FakeVector | None = None,
        layer: int = 0,
        width: int = 250_000,
        net: object | None = None,
        locked: bool = False,
    ) -> None:
        if proto is not None:
            track_id = str(getattr(proto, "id", ""))
            start = _clone_vector(getattr(proto, "start", None))
            end = _clone_vector(getattr(proto, "end", None))
            layer = getattr(proto, "layer", 0)
            width = getattr(proto, "width", 250_000)
            net = getattr(proto, "net", None)
            locked = getattr(proto, "locked", False)

        self.id = track_id
        self.start = start or FakeVector(0, 0)
        self.end = end or FakeVector(0, 0)
        self.layer = layer
        self.width = width
        self.net = net
        self.locked = locked
        self.proto = self

    def length(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return float((dx * dx + dy * dy) ** 0.5)

    def bounding_box(self) -> FakeBox:
        return FakeBox(
            FakeVector(min(self.start.x, self.end.x), min(self.start.y, self.end.y)),
            FakeVector(max(self.start.x, self.end.x), max(self.start.y, self.end.y)),
        )


class FakeMutableVia:
    def __init__(
        self,
        proto: FakeMutableVia | None = None,
        *,
        via_id: str = "",
        position: FakeVector | None = None,
        net: object | None = None,
        diameter: int = 600_000,
        drill_diameter: int = 300_000,
        via_type: int = 1,
        locked: bool = False,
    ) -> None:
        if proto is not None:
            via_id = str(getattr(proto, "id", ""))
            position = _clone_vector(getattr(proto, "position", None))
            net = getattr(proto, "net", None)
            diameter = getattr(proto, "diameter", 600_000)
            drill_diameter = getattr(proto, "drill_diameter", 300_000)
            via_type = getattr(proto, "type", 1)
            locked = getattr(proto, "locked", False)

        self.id = via_id
        self.position = position or FakeVector(0, 0)
        self.net = net
        self.diameter = diameter
        self.drill_diameter = drill_diameter
        self.type = via_type
        self.locked = locked
        self.padstack = FakeViaPadStack()
        self.proto = self


class FakeMutablePolygon:
    def __init__(self, outline: list[FakeVector] | None = None) -> None:
        self.outline = list(outline or [])
        self.holes: list[list[FakeVector]] = []


class FakeMutableZone:
    def __init__(
        self,
        proto: FakeMutableZone | None = None,
        *,
        zone_id: str = "zone-id",
        name: str = "Power Pour",
        net: object | None = None,
        layers: list[int] | None = None,
        locked: bool = False,
        filled: bool = True,
        priority: int = 2,
        zone_type: str = "copper",
        outline: object | None = None,
    ) -> None:
        if proto is not None:
            zone_id = str(getattr(proto, "id", "zone-id"))
            name = getattr(proto, "name", "Power Pour")
            net = getattr(proto, "net", None)
            layers = list(getattr(proto, "layers", [0, 31]))
            locked = getattr(proto, "locked", False)
            filled = getattr(proto, "filled", True)
            priority = getattr(proto, "priority", 2)
            zone_type = getattr(proto, "type", "copper")
            outline = getattr(proto, "outline", None)

        self.id = zone_id
        self.name = name
        self.net = net
        self.layers = list(layers or [0, 31])
        self.locked = locked
        self.filled = filled
        self.priority = priority
        self.type = zone_type
        self.outline = outline or FakeMutablePolygon()
        self.proto = self

    def bounding_box(self) -> FakeBox:
        points = _outline_points(self.outline)
        if not points:
            origin = FakeVector(0, 0)
            return FakeBox(origin, origin)

        return FakeBox(
            FakeVector(min(point.x for point in points), min(point.y for point in points)),
            FakeVector(max(point.x for point in points), max(point.y for point in points)),
        )


class FakeTextAttributes:
    def __init__(
        self,
        proto: FakeTextAttributes | None = None,
        *,
        angle: float = 0.0,
    ) -> None:
        if proto is not None:
            angle = proto.angle

        self.angle = float(angle)
        self.proto = self


class FakeMutableBoardText:
    def __init__(
        self,
        proto: FakeMutableBoardText | None = None,
        *,
        text_id: str = "board-text-id",
        value: str = "",
        layer: int = 37,
        position: FakeVector | None = None,
        locked: bool = False,
        attributes: FakeTextAttributes | None = None,
    ) -> None:
        if proto is not None:
            text_id = str(getattr(proto, "id", text_id))
            value = str(getattr(proto, "value", value))
            layer = getattr(proto, "layer", layer)
            position = _clone_vector(getattr(proto, "position", None))
            locked = getattr(proto, "locked", locked)
            attributes = FakeTextAttributes(getattr(proto, "attributes", None))

        self.id = text_id
        self.value = value
        self.layer = layer
        self.position = position or FakeVector(0, 0)
        self.locked = locked
        self.attributes = attributes or FakeTextAttributes()
        self.proto = self


class FakeMutableBoardTextBox:
    def __init__(
        self,
        proto: FakeMutableBoardTextBox | None = None,
        *,
        text_id: str = "board-textbox-id",
        value: str = "",
        layer: int = 37,
        top_left: FakeVector | None = None,
        bottom_right: FakeVector | None = None,
        locked: bool = False,
        attributes: FakeTextAttributes | None = None,
    ) -> None:
        if proto is not None:
            text_id = str(getattr(proto, "id", text_id))
            value = str(getattr(proto, "value", value))
            layer = getattr(proto, "layer", layer)
            top_left = _clone_vector(getattr(proto, "top_left", None))
            bottom_right = _clone_vector(getattr(proto, "bottom_right", None))
            locked = getattr(proto, "locked", locked)
            attributes = FakeTextAttributes(getattr(proto, "attributes", None))

        self.id = text_id
        self.value = value
        self.layer = layer
        self.top_left = top_left or FakeVector(0, 0)
        self.bottom_right = bottom_right or FakeVector(0, 0)
        self.locked = locked
        self.attributes = attributes or FakeTextAttributes()
        self.proto = self


def _make_fake_field(value: str) -> object:
    return type(
        "FakeField",
        (),
        {"text": type("FakeText", (), {"value": value})()},
    )()


def _clone_vector(vector: object | None) -> FakeVector | None:
    if vector is None or not hasattr(vector, "x") or not hasattr(vector, "y"):
        return None
    return FakeVector(int(vector.x), int(vector.y))


def _outline_points(outline: object | None) -> list[FakeVector]:
    if outline is None:
        return []

    points = getattr(outline, "outline", None)
    if points is None:
        return []
    if hasattr(points, "nodes"):
        points = points.nodes

    resolved_points = []
    for point in points:
        candidate = getattr(point, "point", point)
        cloned = _clone_vector(candidate)
        if cloned is not None:
            resolved_points.append(cloned)
    return resolved_points
