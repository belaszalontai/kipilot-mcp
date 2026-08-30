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


async def test_check_connection_accepts_schematic_endpoint_without_common_ping() -> None:
    class LimitedSchematicEndpoint:
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = FakeSchematic()

        def ping(self) -> None:
            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.Ping"
            )

        def get_open_documents(self, document_type: int) -> list[object]:
            if document_type == 1:
                return [self.schematic.document]

            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.GetOpenDocuments"
            )

        def get_schematic(self) -> FakeSchematic:
            return self.schematic

        def get_api_version(self) -> str:
            return "1.0.0"

        def close(self) -> None:
            pass

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=LimitedSchematicEndpoint)

    result = await client.check_connection()

    assert result == {
        "ok": True,
        "socket_path": None,
        "client_name": "kipilot-mcp",
        "endpoint_types": ["schematic"],
        "api_version": "1.0.0",
        "message": (
            "KiCad IPC endpoint is reachable. The active schematic endpoint does not expose "
            "common Ping/GetVersion requests."
        ),
    }


async def test_get_version_info_reports_unavailable_runtime_version_on_schematic_endpoint() -> None:
    class LimitedSchematicEndpoint:
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = FakeSchematic()

        def get_version(self) -> str:
            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.GetVersion"
            )

        def get_open_documents(self, document_type: int) -> list[object]:
            if document_type == 1:
                return [self.schematic.document]

            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.GetOpenDocuments"
            )

        def get_schematic(self) -> FakeSchematic:
            return self.schematic

        def get_api_version(self) -> str:
            return "1.0.0"

        def close(self) -> None:
            pass

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=LimitedSchematicEndpoint)

    result = await client.get_version_info()

    assert result == {
        "ok": True,
        "socket_path": None,
        "client_name": "kipilot-mcp",
        "endpoint_types": ["schematic"],
        "api_version": "1.0.0",
        "kicad_version": None,
        "api_version_matches_binding": None,
        "message": (
            "KiCad IPC endpoint is reachable. The active schematic endpoint does not expose "
            "GetVersion(), so the runtime KiCad version could not be queried."
        ),
    }


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


async def test_list_open_documents_falls_back_to_explicit_types_for_schematic_endpoint() -> None:
    class SchematicDocumentsOnlyKiCad:
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = FakeSchematic()

        def get_board(self) -> object:
            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.GetOpenDocuments"
            )

        def get_open_documents(self, document_type: int) -> list[object]:
            if document_type == 1:
                return [self.schematic.document]
            if document_type == 6:
                return []

            raise ApiError(
                "KiCad returned error: no handler available for request of type "
                "kiapi.common.commands.GetOpenDocuments"
            )

        def close(self) -> None:
            pass

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=SchematicDocumentsOnlyKiCad)

    result = await client.list_open_documents()

    assert result == {
        "ok": True,
        "count": 1,
        "documents": [
            {
                "type": "2",
                "board_filename": "",
                "path": "C:/demo/demo.kicad_sch",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
            }
        ],
        "document_types": [1, 6],
        "source": "explicit_types_fallback",
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
            "reference": None,
            "footprint_id": None,
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


async def test_get_pads_supports_footprint_filters() -> None:
    class FootprintPadBoard(FakeBoard):
        def __init__(self) -> None:
            self._footprints = [
                FakeMutableFootprint(
                    footprint_id="connector-id",
                    reference="CON301",
                    value="TerminalBlock_1x02",
                    definition_items=[
                        FakeMutablePad(pad_id="pad-a", number="1", net=FakeGroundNet()),
                        FakeMutablePad(pad_id="pad-b", number="2", net=FakePowerNet()),
                    ],
                )
            ]
            self._pads = [
                FakeMutablePad(pad_id="pad-a", number="1", net=FakeGroundNet()),
                FakeMutablePad(pad_id="pad-b", number="2", net=FakePowerNet()),
                FakeMutablePad(pad_id="pad-other", number="1", net=FakeGroundNet()),
            ]

        def get_footprints(self) -> list[FakeMutableFootprint]:
            return list(self._footprints)

        def get_pads(self) -> list[FakeMutablePad]:
            return list(self._pads)

        def get_nets(self) -> list[object]:
            return [FakeGroundNet(), FakePowerNet()]

    class FootprintPadKiCad(FakeBoardKiCad):
        def __init__(self, **_kwargs: object) -> None:
            self.board = FootprintPadBoard()

        def get_board(self) -> FootprintPadBoard:
            return self.board

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FootprintPadKiCad)

    result = await client.get_pads(reference="CON301")

    assert result == {
        "ok": True,
        "count": 2,
        "limit": 200,
        "query": {
            "net_name": None,
            "net": None,
            "layer": None,
            "resolved_layer": None,
            "area": None,
            "reference": "CON301",
            "footprint_id": None,
        },
        "pads": [
            {
                "id": "pad-a",
                "kind": "FakeMutablePad",
                "number": "1",
                "position": {
                    "x_nm": 0,
                    "y_nm": 0,
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                },
                "net": {"name": "GND", "code": 1},
                "pad_type": "thru_hole",
                "layers": [{"id": 0, "name": "F.Cu"}],
                "footprint": {"id": "connector-id", "reference": "CON301"},
            },
            {
                "id": "pad-b",
                "kind": "FakeMutablePad",
                "number": "2",
                "position": {
                    "x_nm": 0,
                    "y_nm": 0,
                    "x_mm": 0.0,
                    "y_mm": 0.0,
                },
                "net": {"name": "12V", "code": 12},
                "pad_type": "thru_hole",
                "layers": [{"id": 0, "name": "F.Cu"}],
                "footprint": {"id": "connector-id", "reference": "CON301"},
            },
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


async def test_get_dimensions_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_dimensions()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "dimensions": [
            {
                "id": "dimension-id",
                "kind": "FakeDimension",
                "layer": {"id": 44, "name": "Edge.Cuts"},
                "locked": False,
                "text": "12.34 mm",
                "override_text_enabled": False,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 1_000_000,
                        "y_nm": 1_000_000,
                        "x_mm": 1.0,
                        "y_mm": 1.0,
                    },
                    "bottom_right": {
                        "x_nm": 5_000_000,
                        "y_nm": 3_000_000,
                        "x_mm": 5.0,
                        "y_mm": 3.0,
                    },
                },
                "start": {
                    "x_nm": 1_000_000,
                    "y_nm": 1_000_000,
                    "x_mm": 1.0,
                    "y_mm": 1.0,
                },
                "end": {
                    "x_nm": 5_000_000,
                    "y_nm": 3_000_000,
                    "x_mm": 5.0,
                    "y_mm": 3.0,
                },
                "height_nm": 1_000_000,
                "height_mm": 1.0,
                "extension_height_nm": 500_000,
                "extension_height_mm": 0.5,
            }
        ],
    }


async def test_get_groups_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_groups()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "groups": [
            {
                "id": "group-id",
                "kind": "FakeGroup",
                "name": "Placement cluster",
                "item_count": 2,
                "item_ids": ["track-id", "shape-silk-1"],
            }
        ],
    }


async def test_get_reference_images_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_reference_images()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "reference_images": [
            {
                "id": "reference-image-id",
                "kind": "FakeReferenceImage",
                "layer": {"id": 37, "name": "F.SilkS"},
                "locked": False,
                "position": {
                    "x_nm": 15_000_000,
                    "y_nm": 5_000_000,
                    "x_mm": 15.0,
                    "y_mm": 5.0,
                },
                "transform_origin_offset": {
                    "x_nm": 500_000,
                    "y_nm": 250_000,
                    "x_mm": 0.5,
                    "y_mm": 0.25,
                },
                "image_scale": 0.5,
                "image_byte_count": 7,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 15_000_000,
                        "y_nm": 5_000_000,
                        "x_mm": 15.0,
                        "y_mm": 5.0,
                    },
                    "bottom_right": {
                        "x_nm": 17_000_000,
                        "y_nm": 6_500_000,
                        "x_mm": 17.0,
                        "y_mm": 6.5,
                    },
                },
            }
        ],
    }


async def test_get_barcodes_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeBoardKiCad)

    result = await client.get_barcodes()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "barcodes": [
            {
                "id": "barcode-id",
                "kind": "FakeBarcode",
                "text": "SN0001",
                "layer": {"id": 37, "name": "F.SilkS"},
                "locked": False,
                "position": {
                    "x_nm": 25_000_000,
                    "y_nm": 12_000_000,
                    "x_mm": 25.0,
                    "y_mm": 12.0,
                },
                "orientation": {
                    "text": "90deg",
                    "degrees": 90.0,
                    "radians": None,
                },
                "barcode_kind": "qr",
                "error_correction": "M",
                "show_text": True,
                "knockout": False,
                "bounding_box": {
                    "top_left": {
                        "x_nm": 25_000_000,
                        "y_nm": 12_000_000,
                        "x_mm": 25.0,
                        "y_mm": 12.0,
                    },
                    "bottom_right": {
                        "x_nm": 31_000_000,
                        "y_nm": 18_000_000,
                        "x_mm": 31.0,
                        "y_mm": 18.0,
                    },
                },
                "width_nm": 6_000_000,
                "width_mm": 6.0,
                "height_nm": 6_000_000,
                "height_mm": 6.0,
                "text_height_nm": 1_200_000,
                "text_height_mm": 1.2,
                "knockout_margin": {
                    "x_nm": 200_000,
                    "y_nm": 200_000,
                    "x_mm": 0.2,
                    "y_mm": 0.2,
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


async def test_set_project_text_variables_dry_run_previews_merged_values() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_project_text_variables(
        {
            "BOARD_REV": "B",
            "BUILD_VARIANT": "PROTO",
        },
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "set_project_text_variables",
        "dry_run": True,
        "commit_message": None,
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
        "merge_mode": "merge",
        "previous_text_variables": {
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
        "requested_text_variables": {
            "count": 2,
            "values": {
                "BOARD_REV": "B",
                "BUILD_VARIANT": "PROTO",
            },
            "variables": [
                {"name": "BOARD_REV", "value": "B"},
                {"name": "BUILD_VARIANT", "value": "PROTO"},
            ],
        },
        "text_variables": {
            "count": 3,
            "values": {
                "AUTHOR": "KiPilot",
                "BOARD_REV": "B",
                "BUILD_VARIANT": "PROTO",
            },
            "variables": [
                {"name": "AUTHOR", "value": "KiPilot"},
                {"name": "BOARD_REV", "value": "B"},
                {"name": "BUILD_VARIANT", "value": "PROTO"},
            ],
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.get_project().calls == []


async def test_set_project_text_variables_updates_project_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_project_text_variables(
        {
            "AUTHOR": "KiPilot Labs",
        },
        merge_mode="replace",
    )

    assert result["ok"] is True
    assert result["mutation"] == "set_project_text_variables"
    assert result["merge_mode"] == "replace"
    assert result["text_variables"] == {
        "count": 1,
        "values": {
            "AUTHOR": "KiPilot Labs",
        },
        "variables": [
            {"name": "AUTHOR", "value": "KiPilot Labs"},
        ],
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.get_project().calls == [
        ("set_text_variables", {"AUTHOR": "KiPilot Labs"}, 2),
    ]


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


async def test_get_selection_returns_serialized_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_selection()

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "selection": [
            {
                "id": "track-id",
                "kind": "FakeMutableTrack",
                "layer": {"id": 0, "name": "F.Cu"},
                "locked": False,
                "net": {"name": "+3V3", "code": 7},
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


async def test_add_to_selection_dry_run_previews_result() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.add_to_selection(item_ids=["footprint-id"], dry_run=True)

    assert result["ok"] is True
    assert result["mutation"] == "add_to_selection"
    assert result["dry_run"] is True
    assert result["requested_item_ids"] == ["footprint-id"]
    assert result["previous_count"] == 1
    assert result["count"] == 2
    assert [item["id"] for item in result["selection"]] == ["track-id", "footprint-id"]
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_remove_from_selection_updates_selection_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.remove_from_selection(item_ids=["track-id"])

    assert result["ok"] is True
    assert result["mutation"] == "remove_from_selection"
    assert result["previous_count"] == 1
    assert result["count"] == 0
    assert result["selection"] == []
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("remove_from_selection", ["track-id"]),
    ]


async def test_clear_selection_clears_items_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.clear_selection()

    assert result["ok"] is True
    assert result["mutation"] == "clear_selection"
    assert result["previous_count"] == 1
    assert result["count"] == 0
    assert result["selection"] == []
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [("clear_selection",)]


async def test_get_graphics_defaults_returns_serialized_defaults() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_graphics_defaults()

    assert result == {
        "ok": True,
        "count": 2,
        "graphics_defaults": [
            {
                "layer_class": 1,
                "line_thickness_nm": 150_000,
                "line_thickness_mm": 0.15,
                "text_attributes": {
                    "font_name": "KiCad Font",
                    "angle_degrees": 0.0,
                    "line_spacing": 1.0,
                    "italic": False,
                    "bold": False,
                    "underlined": False,
                    "mirrored": False,
                    "multiline": False,
                    "keep_upright": True,
                    "size": {
                        "x_nm": 1_000_000,
                        "y_nm": 1_200_000,
                        "x_mm": 1.0,
                        "y_mm": 1.2,
                    },
                    "horizontal_alignment": 1,
                    "vertical_alignment": 2,
                    "stroke_width_nm": 120_000,
                    "stroke_width_mm": 0.12,
                },
            },
            {
                "layer_class": 2,
                "line_thickness_nm": 200_000,
                "line_thickness_mm": 0.2,
                "text_attributes": {
                    "font_name": "KiCad Sans",
                    "angle_degrees": 90.0,
                    "line_spacing": 1.1,
                    "italic": True,
                    "bold": True,
                    "underlined": False,
                    "mirrored": False,
                    "multiline": True,
                    "keep_upright": False,
                    "size": {
                        "x_nm": 1_500_000,
                        "y_nm": 1_500_000,
                        "x_mm": 1.5,
                        "y_mm": 1.5,
                    },
                    "horizontal_alignment": 2,
                    "vertical_alignment": 3,
                    "stroke_width_nm": 180_000,
                    "stroke_width_mm": 0.18,
                },
            },
        ],
    }


async def test_get_editor_appearance_settings_returns_current_values() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_editor_appearance_settings()

    assert result == {
        "ok": True,
        "appearance_settings": {
            "inactive_layer_display": 1,
            "net_color_display": 2,
            "board_flip": 1,
            "ratsnest_display": 3,
        },
    }


async def test_set_editor_appearance_settings_dry_run_previews_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_editor_appearance_settings(
        board_flip=2,
        ratsnest_display=1,
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "set_editor_appearance_settings",
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
        "previous_appearance_settings": {
            "inactive_layer_display": 1,
            "net_color_display": 2,
            "board_flip": 1,
            "ratsnest_display": 3,
        },
        "appearance_settings": {
            "inactive_layer_display": 1,
            "net_color_display": 2,
            "board_flip": 2,
            "ratsnest_display": 1,
        },
        "requested_changes": {
            "board_flip": 2,
            "ratsnest_display": 1,
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_set_editor_appearance_settings_updates_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_editor_appearance_settings(
        inactive_layer_display=4,
        net_color_display=5,
    )

    assert result["ok"] is True
    assert result["mutation"] == "set_editor_appearance_settings"
    assert result["appearance_settings"] == {
        "inactive_layer_display": 4,
        "net_color_display": 5,
        "board_flip": 1,
        "ratsnest_display": 3,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("set_editor_appearance_settings", 4, 5, 1, 3),
    ]


async def test_get_items_filters_by_requested_kinds() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_items(item_kinds=["footprints", "tracks"])

    assert result["ok"] is True
    assert result["count"] == 3
    assert result["item_kinds"] == ["footprints", "tracks"]
    assert [item["id"] for item in result["items"]] == [
        "footprint-id",
        "footprint-b-id",
        "track-id",
    ]


async def test_get_items_by_id_returns_requested_order() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_items_by_id(["via-id", "footprint-id"])

    assert result["ok"] is True
    assert result["count"] == 2
    assert result["item_ids"] == ["via-id", "footprint-id"]
    assert [item["id"] for item in result["items"]] == ["via-id", "footprint-id"]


async def test_hit_test_returns_true_for_point_inside_track_bounds() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.hit_test(item_id="track-id", x_mm=3.0, y_mm=2.0)

    assert result == {
        "ok": True,
        "item": {
            "id": "track-id",
            "kind": "FakeMutableTrack",
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
        "position": {
            "x_nm": 3_000_000,
            "y_nm": 2_000_000,
            "x_mm": 3.0,
            "y_mm": 2.0,
        },
        "tolerance_nm": 0,
        "tolerance_mm": 0.0,
        "hit": True,
    }


async def test_get_text_extents_returns_bounding_box_for_board_text() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_text_extents(text_item_id="board-text-id")

    assert result["ok"] is True
    assert result["item"]["id"] == "board-text-id"
    assert result["bounding_box"] == {
        "top_left": {
            "x_nm": 20_000_000,
            "y_nm": 10_000_000,
            "x_mm": 20.0,
            "y_mm": 10.0,
        },
        "bottom_right": {
            "x_nm": 27_000_000,
            "y_nm": 11_000_000,
            "x_mm": 27.0,
            "y_mm": 11.0,
        },
    }


async def test_get_text_as_shapes_returns_compound_shapes_for_text_items() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_text_as_shapes(text_item_ids=["board-text-id", "board-textbox-id"])

    assert result["ok"] is True
    assert result["count"] == 2
    assert result["item_ids"] == ["board-text-id", "board-textbox-id"]
    assert result["items"][0]["item"]["id"] == "board-text-id"
    assert result["items"][0]["shape_count"] == 1
    assert result["items"][0]["shapes"][0]["id"] == "board-text-id-shape"
    assert result["items"][1]["item"]["id"] == "board-textbox-id"
    assert result["items"][1]["shape_count"] == 1
    assert result["items"][1]["shapes"][0]["id"] == "board-textbox-id-shape"


async def test_save_board_as_dry_run_previews_target_file() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.save_board_as(
        filename="C:/demo/output/demo-copy.kicad_pcb",
        overwrite=True,
        include_project=False,
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "save_board_as",
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
        "saved_filename": "C:/demo/output/demo-copy.kicad_pcb",
        "overwrite": True,
        "include_project": False,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_save_board_as_executes_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.save_board_as(filename="C:/demo/output/demo-copy.kicad_pcb")

    assert result["ok"] is True
    assert result["saved_filename"] == "C:/demo/output/demo-copy.kicad_pcb"
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("save_as", "C:/demo/output/demo-copy.kicad_pcb", False, True),
    ]


async def test_check_padstack_presence_on_layers_returns_presence_matrix() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.check_padstack_presence_on_layers(
        item_ids=["via-id", "pad-id"],
        layers=["F.Cu", "B.Cu"],
    )

    assert result == {
        "ok": True,
        "count": 2,
        "item_ids": ["via-id", "pad-id"],
        "resolved_layers": [
            {"id": 0, "name": "F.Cu"},
            {"id": 31, "name": "B.Cu"},
        ],
        "items": [
            {
                "item": {
                    "id": "via-id",
                    "kind": "FakeMutableVia",
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
                    "type": 1,
                },
                "layers": [
                    {"layer": {"id": 0, "name": "F.Cu"}, "present": True},
                    {"layer": {"id": 31, "name": "B.Cu"}, "present": True},
                ],
            },
            {
                "item": {
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
                    "layers": [{"id": 0, "name": "F.Cu"}],
                },
                "layers": [
                    {"layer": {"id": 0, "name": "F.Cu"}, "present": True},
                    {"layer": {"id": 31, "name": "B.Cu"}, "present": False},
                ],
            },
        ],
    }


async def test_get_pad_shapes_as_polygons_returns_polygonized_pads() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeMutationKiCad)

    result = await client.get_pad_shapes_as_polygons(pad_ids=["pad-id"], layer="F.Cu")

    assert result == {
        "ok": True,
        "count": 1,
        "limit": 200,
        "pad_ids": ["pad-id"],
        "resolved_layer": {"id": 0, "name": "F.Cu"},
        "items": [
            {
                "pad": {
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
                    "layers": [{"id": 0, "name": "F.Cu"}],
                },
                "polygon": {
                    "outline": [
                        {"x_nm": 1_750_000, "y_nm": 3_750_000, "x_mm": 1.75, "y_mm": 3.75},
                        {"x_nm": 2_250_000, "y_nm": 3_750_000, "x_mm": 2.25, "y_mm": 3.75},
                        {"x_nm": 2_250_000, "y_nm": 4_250_000, "x_mm": 2.25, "y_mm": 4.25},
                        {"x_nm": 1_750_000, "y_nm": 4_250_000, "x_mm": 1.75, "y_mm": 4.25},
                    ]
                },
            }
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


async def test_get_schematic_hierarchy_returns_serialized_tree() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.get_schematic_hierarchy()

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "count": 1,
        "hierarchy": [
            {
                "name": "Root",
                "filename": "demo.kicad_sch",
                "page_number": "1",
                "path": {
                    "ids": ["root-sheet"],
                    "text": "/root-sheet",
                    "human_readable": "/Root",
                },
                "children": [
                    {
                        "name": "Power",
                        "filename": "power.kicad_sch",
                        "page_number": "2",
                        "path": {
                            "ids": ["root-sheet", "power-sheet"],
                            "text": "/root-sheet/power-sheet",
                            "human_readable": "/Root/Power",
                        },
                        "children": [],
                    }
                ],
            }
        ],
    }


async def test_get_schematic_netlist_returns_serialized_nets() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.get_schematic_netlist(item_types=[1001])

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "count": 1,
        "item_types": [1001],
        "nets": [
            {
                "name": "+3V3",
                "sheets": [
                    {
                        "path": {
                            "ids": ["root-sheet"],
                            "text": "/root-sheet",
                            "human_readable": "/Root",
                        },
                        "item_ids": ["symbol-1", "label-1"],
                    }
                ],
            }
        ],
    }


async def test_get_schematic_page_settings_returns_serialized_settings() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.get_schematic_page_settings()

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "page_settings": {
            "page_size": 5,
            "orientation": 1,
            "drawing_sheet": "A4.kicad_wks",
            "user_page_size": {
                "x_nm": 210_000_000,
                "y_nm": 297_000_000,
                "x_mm": 210.0,
                "y_mm": 297.0,
            },
        },
    }


async def test_get_schematic_title_block_returns_serialized_metadata() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.get_schematic_title_block()

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "title_block": {
            "title": "Demo Schematic",
            "revision": "A",
            "date": "2026-05-19",
            "company": "KiPilot Labs",
            "comments": {
                "1": "Main sheet",
                "2": "Internal",
            },
        },
    }


async def test_hit_test_schematic_returns_true_for_point_inside_item_bounds() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.hit_test_schematic(item_id="symbol-1", x_mm=3.0, y_mm=2.0)

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "item_id": "symbol-1",
        "position": {
            "x_nm": 3_000_000,
            "y_nm": 2_000_000,
            "x_mm": 3.0,
            "y_mm": 2.0,
        },
        "tolerance_nm": 0,
        "tolerance_mm": 0.0,
        "hit": True,
    }


async def test_hit_test_schematic_reports_missing_runtime_support() -> None:
    class SchematicWithoutHitTestKiCad(FakeSchematicKiCad):
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = FakeSchematicWithoutHitTest()

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=SchematicWithoutHitTestKiCad)

    result = await client.hit_test_schematic(item_id="symbol-1", x_mm=3.0, y_mm=2.0)

    assert result == {
        "ok": False,
        "message": "The active KiCad schematic does not expose hit_test().",
        "error": "The active KiCad schematic does not expose hit_test().",
    }


async def test_export_schematic_svg_returns_job_summary() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.export_schematic_svg("C:/exports/svg-output")

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "format": "svg",
        "output_kind": "directory",
        "output_path": "C:/exports/svg-output",
        "output_dir": "C:/exports/svg-output",
        "requested_plot_settings": None,
        "requested_options": None,
        "job": {
            "succeeded": True,
            "status": 1,
            "output_paths": ["C:/exports/svg-output"],
            "message": "SVG export completed.",
        },
    }


async def test_export_schematic_pdf_passes_plot_settings_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    monkeypatch.setattr(
        KiCadIpcClient,
        "_create_schematic_plot_settings",
        lambda self, plot_settings: FakeSchematicPlotSettings(plot_settings),
    )

    result = await client.export_schematic_pdf(
        "C:/exports/demo.pdf",
        plot_settings={
            "drawing_sheet": "A4.kicad_wks",
            "plot_all": True,
            "plot_pages": ["/", "/Power"],
            "page_size": 2,
            "theme": "Plot",
        },
        property_popups=True,
        hierarchical_links=True,
        include_metadata=False,
    )

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "format": "pdf",
        "output_kind": "file",
        "output_path": "C:/exports/demo.pdf",
        "output_file": "C:/exports/demo.pdf",
        "requested_plot_settings": {
            "drawing_sheet": "A4.kicad_wks",
            "default_font": "",
            "variant": "",
            "plot_all": True,
            "plot_drawing_sheet": False,
            "plot_pages": ["/", "/Power"],
            "show_hop_over": False,
            "black_and_white": False,
            "page_size": 2,
            "use_background_color": False,
            "min_pen_width": 0,
            "theme": "Plot",
        },
        "requested_options": {
            "property_popups": True,
            "hierarchical_links": True,
            "include_metadata": False,
        },
        "job": {
            "succeeded": True,
            "status": 1,
            "output_paths": ["C:/exports/demo.pdf"],
            "message": "PDF export completed.",
        },
    }


async def test_export_schematic_netlist_returns_job_summary() -> None:
    FakeSchematicKiCad.last_instance = None
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.export_schematic_netlist(
        "C:/exports/demo.net",
        netlist_format=8,
        variant_name="Assembly",
    )

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "job_type": "netlist",
        "netlist_format": 8,
        "variant_name": "Assembly",
        "output_kind": "file",
        "output_path": "C:/exports/demo.net",
        "output_file": "C:/exports/demo.net",
        "job": {
            "succeeded": True,
            "status": 1,
            "output_paths": ["C:/exports/demo.net"],
            "message": "Netlist export completed.",
        },
    }

    assert FakeSchematicKiCad.last_instance is not None
    assert FakeSchematicKiCad.last_instance.schematic.last_export_netlist_call == {
        "output_path": "C:/exports/demo.net",
        "format": 8,
        "variant_name": "Assembly",
    }


async def test_export_schematic_bom_passes_settings_and_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeSchematicKiCad.last_instance = None
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    monkeypatch.setattr(
        KiCadIpcClient,
        "_create_schematic_bom_format_settings",
        lambda self, format_settings: FakeSchematicBomFormatSettings(format_settings),
    )
    monkeypatch.setattr(
        KiCadIpcClient,
        "_create_schematic_bom_field_settings",
        lambda self, field_settings: FakeSchematicBomFieldSettings(field_settings),
    )

    result = await client.export_schematic_bom(
        "C:/exports/demo.csv",
        format_settings={
            "preset_name": "CSV",
            "field_delimiter": ";",
            "string_delimiter": '"',
            "ref_delimiter": ",",
            "ref_range_delimiter": "-",
            "keep_tabs": True,
            "keep_line_breaks": True,
        },
        field_settings={
            "preset_name": "Grouped By Value",
            "fields": [
                {"name": "Reference", "label": "Refs", "group_by": True},
                {"name": "Value", "label": "Value", "group_by": True},
            ],
            "sort_field": "Reference",
            "sort_direction": 2,
            "filter": "${DNP} != 1",
        },
        exclude_dnp=True,
        group_symbols=True,
        variant_name="Assembly",
    )

    assert result == {
        "ok": True,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "job_type": "bom",
        "output_kind": "file",
        "output_path": "C:/exports/demo.csv",
        "output_file": "C:/exports/demo.csv",
        "requested_format_settings": {
            "preset_name": "CSV",
            "field_delimiter": ";",
            "string_delimiter": '"',
            "ref_delimiter": ",",
            "ref_range_delimiter": "-",
            "keep_tabs": True,
            "keep_line_breaks": True,
        },
        "requested_field_settings": {
            "preset_name": "Grouped By Value",
            "fields": [
                {"name": "Reference", "label": "Refs", "group_by": True},
                {"name": "Value", "label": "Value", "group_by": True},
            ],
            "sort_field": "Reference",
            "sort_direction": 2,
            "filter": "${DNP} != 1",
        },
        "requested_options": {
            "exclude_dnp": True,
            "group_symbols": True,
            "variant_name": "Assembly",
        },
        "job": {
            "succeeded": True,
            "status": 1,
            "output_paths": ["C:/exports/demo.csv"],
            "message": "BOM export completed.",
        },
    }

    assert FakeSchematicKiCad.last_instance is not None
    assert FakeSchematicKiCad.last_instance.schematic.last_export_bom_call == {
        "output_path": "C:/exports/demo.csv",
        "format_settings": FakeSchematicBomFormatSettings(
            {
                "preset_name": "CSV",
                "field_delimiter": ";",
                "string_delimiter": '"',
                "ref_delimiter": ",",
                "ref_range_delimiter": "-",
                "keep_tabs": True,
                "keep_line_breaks": True,
            }
        ),
        "field_settings": FakeSchematicBomFieldSettings(
            {
                "preset_name": "Grouped By Value",
                "fields": [
                    {"name": "Reference", "label": "Refs", "group_by": True},
                    {"name": "Value", "label": "Value", "group_by": True},
                ],
                "sort_field": "Reference",
                "sort_direction": 2,
                "filter": "${DNP} != 1",
            }
        ),
        "exclude_dnp": True,
        "group_symbols": True,
        "variant_name": "Assembly",
    }


async def test_export_schematic_svg_rejects_file_like_output_path() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.export_schematic_svg("C:/exports/demo.svg")

    assert result == {
        "ok": False,
        "message": (
            "output_dir must point to an output directory for schematic SVG export, "
            "not a .svg file path."
        ),
        "error": (
            "output_dir must point to an output directory for schematic SVG export, "
            "not a .svg file path."
        ),
    }


async def test_export_schematic_pdf_rejects_directory_like_output_path() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.export_schematic_pdf("C:/exports/pdf-output/")

    assert result == {
        "ok": False,
        "message": (
            "output_file must point to an output file for schematic PDF export, "
            "not a directory path."
        ),
        "error": (
            "output_file must point to an output file for schematic PDF export, "
            "not a directory path."
        ),
    }


async def test_export_schematic_netlist_rejects_directory_like_output_path() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FakeSchematicKiCad)

    result = await client.export_schematic_netlist("C:/exports/netlist-output/")

    assert result == {
        "ok": False,
        "message": (
            "output_file must point to an output file for schematic NETLIST export, "
            "not a directory path."
        ),
        "error": (
            "output_file must point to an output file for schematic NETLIST export, "
            "not a directory path."
        ),
    }


async def test_export_schematic_plot_job_reports_missing_runtime_support() -> None:
    class SchematicWithoutPlotExports(FakeSchematicKiCad):
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = FakeSchematicWithoutExports()

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=SchematicWithoutPlotExports)

    result = await client.export_schematic_ps("C:/exports/ps-output")

    assert result == {
        "ok": False,
        "message": "The active KiCad schematic does not expose export_ps().",
        "error": "The active KiCad schematic does not expose export_ps().",
    }


async def test_export_schematic_bom_reports_missing_runtime_support() -> None:
    class SchematicWithoutBomExport(FakeSchematicKiCad):
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = FakeSchematicWithoutExports()

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=SchematicWithoutBomExport)

    result = await client.export_schematic_bom("C:/exports/demo.csv")

    assert result == {
        "ok": False,
        "message": "The active KiCad schematic does not expose export_bom().",
        "error": "The active KiCad schematic does not expose export_bom().",
    }


async def test_get_schematic_hierarchy_reports_missing_runtime_support() -> None:
    class PcbOnlyKiCad:
        def __init__(self, **_: object) -> None:
            pass

        def close(self) -> None:
            pass

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=PcbOnlyKiCad)

    result = await client.get_schematic_hierarchy()

    assert result == {
        "ok": False,
        "message": (
            "The installed kicad-python runtime does not expose KiCad.get_schematic(). "
            "Schematic MCP tools require a newer binding build with schematic IPC support."
        ),
        "error": (
            "The installed kicad-python runtime does not expose KiCad.get_schematic(). "
            "Schematic MCP tools require a newer binding build with schematic IPC support."
        ),
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


async def test_find_footprints_includes_child_graphics_summary() -> None:
    class FootprintArtworkBoard(FakeBoard):
        def get_footprints(self) -> list[FakeMutableFootprint]:
            return [
                FakeMutableFootprint(
                    footprint_id="logo-footprint-id",
                    reference="LOGO",
                    value="LOGO",
                    position=FakeVector(10_000_000, 20_000_000),
                    orientation=FakeAngle(0),
                    layer=0,
                    definition_items=[
                        FakeMutableBoardPolygon(
                            shape_id="logo-shape-1",
                            layer=37,
                            polygons=[
                                FakeMutablePolygon(
                                    outline=[
                                        FakeVector(9_000_000, 19_000_000),
                                        FakeVector(11_000_000, 19_000_000),
                                        FakeVector(11_000_000, 21_000_000),
                                    ]
                                )
                            ],
                        ),
                        FakeMutableBoardPolygon(
                            shape_id="logo-shape-2",
                            layer=37,
                            polygons=[
                                FakeMutablePolygon(
                                    outline=[
                                        FakeVector(9_500_000, 19_500_000),
                                        FakeVector(10_500_000, 19_500_000),
                                        FakeVector(10_500_000, 20_500_000),
                                    ]
                                )
                            ],
                        ),
                    ],
                )
            ]

    class FootprintArtworkKiCad(FakeBoardKiCad):
        def __init__(self, **_kwargs: object) -> None:
            self.board = FootprintArtworkBoard()

        def get_board(self) -> FootprintArtworkBoard:
            return self.board

    client = KiCadIpcClient(KiCadIpcConfig(), kicad_factory=FootprintArtworkKiCad)

    result = await client.find_footprints(text_query="LOGO", limit=5)

    assert result["count"] == 1
    assert result["footprints"][0]["child_graphics"] == {
        "count": 2,
        "layers": [
            {
                "layer": {"id": 37, "name": "F.SilkS"},
                "count": 2,
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
    assert "does not expose this request" in str(result["message"])
    assert "Open the target editor" in str(result["message"])


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


async def test_flip_footprint_dry_run_previews_opposite_layer() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.flip_footprint(reference="R1", dry_run=True)

    assert result == {
        "ok": True,
        "mutation": "flip_footprint",
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
            "orientation": "-90deg",
            "layer": 31,
            "locked": False,
        },
        "previous_layer": {"id": 0, "name": "F.Cu"},
        "target_layer": {"id": 31, "name": "B.Cu"},
        "mirrored": True,
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == []


async def test_flip_footprint_updates_board_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.flip_footprint(footprint_id="footprint-id")

    assert result["ok"] is True
    assert result["mutation"] == "flip_footprint"
    assert result["dry_run"] is False
    assert result["commit_message"] == "KiPilot MCP: flip_footprint"
    assert result["footprint"]["layer"] == 31
    assert result["target_layer"] == {"id": 31, "name": "B.Cu"}
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["footprint-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: flip_footprint"),
    ]


async def test_update_footprint_pad_net_dry_run_previews_pad_change() -> None:
    class PadNetMutationBoard(FakeMutationBoard):
        def __init__(self) -> None:
            super().__init__()
            self._footprints = [
                FakeMutableFootprint(
                    footprint_id="connector-id",
                    reference="CON301",
                    value="TerminalBlock_1x04",
                    position=FakeVector(142_100_000, 28_100_000),
                    orientation=FakeAngle(180),
                    layer=0,
                    definition_items=[
                        FakeMutablePad(pad_id="pad-1", number="1", net=FakeGroundNet()),
                        FakeMutablePad(pad_id="pad-2", number="2", net=FakeGroundNet()),
                    ],
                )
            ]

        def get_nets(self) -> list[object]:
            return [FakeGroundNet(), FakePowerNet()]

    class PadNetMutationKiCad(FakeBoardKiCad):
        last_instance: PadNetMutationKiCad | None = None

        def __init__(self, **_kwargs: object) -> None:
            self.board = PadNetMutationBoard()
            type(self).last_instance = self

        def get_board(self) -> PadNetMutationBoard:
            return self.board

    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=False),
        kicad_factory=PadNetMutationKiCad,
    )

    result = await client.update_footprint_pad_net(
        reference="CON301",
        pad_number="2",
        net_name="12V",
        expected_current_net_name="GND",
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "update_footprint_pad_net",
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
            "reference": "CON301",
            "footprint_id": None,
            "pad_number": "2",
            "pad_id": None,
        },
        "previous_footprint": {
            "id": "connector-id",
            "reference": "CON301",
            "value": "TerminalBlock_1x04",
            "position": {
                "x_nm": 142_100_000,
                "y_nm": 28_100_000,
                "x_mm": 142.1,
                "y_mm": 28.1,
            },
            "orientation": "180deg",
            "layer": 0,
            "locked": False,
        },
        "footprint": {
            "id": "connector-id",
            "reference": "CON301",
            "value": "TerminalBlock_1x04",
            "position": {
                "x_nm": 142_100_000,
                "y_nm": 28_100_000,
                "x_mm": 142.1,
                "y_mm": 28.1,
            },
            "orientation": "180deg",
            "layer": 0,
            "locked": False,
        },
        "previous_pad": {
            "id": "pad-2",
            "kind": "FakeMutablePad",
            "number": "2",
            "position": {
                "x_nm": 0,
                "y_nm": 0,
                "x_mm": 0.0,
                "y_mm": 0.0,
            },
            "net": {"name": "GND", "code": 1},
            "pad_type": "thru_hole",
            "layers": [{"id": 0, "name": "F.Cu"}],
            "footprint": {"id": "connector-id", "reference": "CON301"},
        },
        "pad": {
            "id": "pad-2",
            "kind": "FakeMutablePad",
            "number": "2",
            "position": {
                "x_nm": 0,
                "y_nm": 0,
                "x_mm": 0.0,
                "y_mm": 0.0,
            },
            "net": {"name": "12V", "code": 12},
            "pad_type": "thru_hole",
            "layers": [{"id": 0, "name": "F.Cu"}],
            "footprint": {"id": "connector-id", "reference": "CON301"},
        },
        "requested_changes": {
            "net": {"name": "12V", "code": 12},
            "expected_current_net_name": "GND",
        },
    }
    assert PadNetMutationKiCad.last_instance is not None
    assert PadNetMutationKiCad.last_instance.board.calls == []


async def test_update_footprint_pad_net_updates_board_when_enabled() -> None:
    class PadNetMutationBoard(FakeMutationBoard):
        def __init__(self) -> None:
            super().__init__()
            self._footprints = [
                FakeMutableFootprint(
                    footprint_id="connector-id",
                    reference="CON301",
                    value="TerminalBlock_1x04",
                    position=FakeVector(142_100_000, 28_100_000),
                    orientation=FakeAngle(180),
                    layer=0,
                    definition_items=[
                        FakeMutablePad(pad_id="pad-1", number="1", net=FakeGroundNet()),
                        FakeMutablePad(pad_id="pad-2", number="2", net=FakeGroundNet()),
                    ],
                )
            ]

        def get_nets(self) -> list[object]:
            return [FakeGroundNet(), FakePowerNet()]

    class PadNetMutationKiCad(FakeBoardKiCad):
        last_instance: PadNetMutationKiCad | None = None

        def __init__(self, **_kwargs: object) -> None:
            self.board = PadNetMutationBoard()
            type(self).last_instance = self

        def get_board(self) -> PadNetMutationBoard:
            return self.board

    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=True),
        kicad_factory=PadNetMutationKiCad,
    )

    result = await client.update_footprint_pad_net(
        footprint_id="connector-id",
        pad_number="2",
        net_name="12V",
        expected_current_net_name="GND",
    )

    assert result["ok"] is True
    assert result["mutation"] == "update_footprint_pad_net"
    assert result["dry_run"] is False
    assert result["commit_message"] == "KiPilot MCP: update_footprint_pad_net"
    assert result["pad"]["net"] == {"name": "12V", "code": 12}
    assert PadNetMutationKiCad.last_instance is not None
    assert PadNetMutationKiCad.last_instance.board.calls == [
        ("begin_commit",),
        ("update_items", ["connector-id"]),
        ("push_commit", "fake-commit", "KiPilot MCP: update_footprint_pad_net"),
    ]


async def test_flip_footprint_supports_named_copper_layers_with_noncanonical_ids() -> None:
    class DynamicLayerMutationBoard(FakeMutationBoard):
        def __init__(self) -> None:
            super().__init__()
            self._active_layer = 3
            self._visible_layers = [3, 2, 44]
            self._enabled_layers = [3, 2, 44]
            self._footprints[0].layer = 3
            self._footprints[1].layer = 2

        def get_layer_name(self, layer: int) -> str:
            names = {
                2: "B.Cu",
                3: "F.Cu",
                36: "B.SilkS",
                37: "F.SilkS",
                44: "Edge.Cuts",
            }
            return names.get(layer, "")

    class DynamicLayerMutationKiCad(FakeBoardKiCad):
        last_instance: DynamicLayerMutationKiCad | None = None

        def __init__(self, **_kwargs: object) -> None:
            self.board = DynamicLayerMutationBoard()
            type(self).last_instance = self

        def get_board(self) -> DynamicLayerMutationBoard:
            return self.board

    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=False),
        kicad_factory=DynamicLayerMutationKiCad,
    )

    result = await client.flip_footprint(
        footprint_id="footprint-id",
        target_layer="B.Cu",
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["previous_layer"] == {"id": 3, "name": "F.Cu"}
    assert result["target_layer"] == {"id": 2, "name": "B.Cu"}
    assert result["footprint"]["layer"] == 2
    assert DynamicLayerMutationKiCad.last_instance is not None
    assert DynamicLayerMutationKiCad.last_instance.board.calls == []


async def test_flip_footprint_dry_run_reports_child_graphics_summary() -> None:
    class FootprintArtworkMutationBoard(FakeMutationBoard):
        def __init__(self) -> None:
            super().__init__()
            self._footprints = [
                FakeMutableFootprint(
                    footprint_id="logo-footprint-id",
                    reference="LOGO",
                    value="LOGO",
                    position=FakeVector(10_000_000, 20_000_000),
                    orientation=FakeAngle(0),
                    layer=0,
                    definition_items=[
                        FakeMutableBoardPolygon(
                            shape_id="logo-shape-1",
                            layer=37,
                            polygons=[
                                FakeMutablePolygon(
                                    outline=[
                                        FakeVector(9_000_000, 19_000_000),
                                        FakeVector(11_000_000, 19_000_000),
                                        FakeVector(11_000_000, 21_000_000),
                                    ]
                                )
                            ],
                        ),
                        FakeMutableBoardPolygon(
                            shape_id="logo-shape-2",
                            layer=37,
                            polygons=[
                                FakeMutablePolygon(
                                    outline=[
                                        FakeVector(9_500_000, 19_500_000),
                                        FakeVector(10_500_000, 19_500_000),
                                        FakeVector(10_500_000, 20_500_000),
                                    ]
                                )
                            ],
                        ),
                    ],
                )
            ]

    class FootprintArtworkMutationKiCad(FakeBoardKiCad):
        def __init__(self, **_kwargs: object) -> None:
            self.board = FootprintArtworkMutationBoard()

        def get_board(self) -> FootprintArtworkMutationBoard:
            return self.board

    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=False),
        kicad_factory=FootprintArtworkMutationKiCad,
    )

    result = await client.flip_footprint(
        footprint_id="logo-footprint-id",
        target_layer="B.Cu",
        dry_run=True,
    )

    assert result["mirrored"] is True
    assert result["previous_footprint"]["child_graphics"] == {
        "count": 2,
        "layers": [
            {
                "layer": {"id": 37, "name": "F.SilkS"},
                "count": 2,
            }
        ],
    }
    assert result["footprint"]["child_graphics"] == {
        "count": 2,
        "layers": [
            {
                "layer": {"id": 36, "name": "B.SilkS"},
                "count": 2,
            }
        ],
    }


def test_apply_footprint_side_flip_mirrors_graphic_children_and_fields() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)
    board = FakeMutationBoard()
    footprint = FakeMutableFootprint(
        footprint_id="logo-footprint-id",
        reference="LOGO",
        value="LOGO",
        position=FakeVector(10_000_000, 20_000_000),
        orientation=FakeAngle(90),
        layer=0,
        definition_items=[
            FakeMutableBoardPolygon(
                shape_id="logo-shape-id",
                layer=37,
                polygons=[
                    FakeMutablePolygon(
                        outline=[
                            FakeVector(9_000_000, 19_000_000),
                            FakeVector(11_000_000, 19_000_000),
                            FakeVector(11_000_000, 21_000_000),
                        ]
                    )
                ],
            )
        ],
    )
    footprint.reference_field.text.position = FakeVector(12_000_000, 21_000_000)
    footprint.reference_field.text.layer = 37
    footprint.reference_field.text.attributes = FakeTextAttributes(angle=0.0, mirrored=False)

    did_flip = client._apply_footprint_side_flip(board, footprint, target_layer=31)

    assert did_flip is True
    assert str(footprint.orientation) == "-90deg"
    assert footprint.layer == 31
    assert footprint.reference_field.text.position.x == 8_000_000
    assert footprint.reference_field.text.position.y == 21_000_000
    assert footprint.reference_field.text.layer == 36
    assert footprint.reference_field.text.attributes.mirrored is True

    polygon = footprint.definition.items[0]
    assert polygon.layer == 36
    assert [(point.x, point.y) for point in polygon.polygons[0].outline] == [
        (11_000_000, 19_000_000),
        (9_000_000, 19_000_000),
        (9_000_000, 21_000_000),
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


async def test_set_schematic_page_settings_requires_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_schematic_page_settings(dry_run=True)

    assert result["ok"] is False
    assert result["message"] == "At least one page settings field must be provided."


async def test_set_schematic_page_settings_dry_run_previews_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_schematic_page_settings(
        page_size=6,
        drawing_sheet="A3.kicad_wks",
        user_page_size_mm={"x_mm": 420.0, "y_mm": 297.0},
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "sch_set_page_settings",
        "dry_run": True,
        "commit_message": None,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "previous_page_settings": {
            "page_size": 5,
            "orientation": 1,
            "drawing_sheet": "A4.kicad_wks",
            "user_page_size": {
                "x_nm": 210_000_000,
                "y_nm": 297_000_000,
                "x_mm": 210.0,
                "y_mm": 297.0,
            },
        },
        "page_settings": {
            "page_size": 6,
            "orientation": 1,
            "drawing_sheet": "A3.kicad_wks",
            "user_page_size": {
                "x_nm": 420_000_000,
                "y_nm": 297_000_000,
                "x_mm": 420.0,
                "y_mm": 297.0,
            },
        },
        "requested_changes": {
            "page_size": 6,
            "orientation": None,
            "drawing_sheet": "A3.kicad_wks",
            "user_page_size": {
                "x_nm": 420_000_000,
                "y_nm": 297_000_000,
                "x_mm": 420.0,
                "y_mm": 297.0,
            },
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.schematic.calls == []


async def test_set_schematic_page_settings_updates_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_schematic_page_settings(orientation=2)

    assert result["ok"] is True
    assert result["mutation"] == "sch_set_page_settings"
    assert result["page_settings"] == {
        "page_size": 5,
        "orientation": 2,
        "drawing_sheet": "A4.kicad_wks",
        "user_page_size": {
            "x_nm": 210_000_000,
            "y_nm": 297_000_000,
            "x_mm": 210.0,
            "y_mm": 297.0,
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.schematic.calls == [
        ("begin_commit",),
        ("set_page_settings", 5, 2, "A4.kicad_wks", 210_000_000, 297_000_000),
        ("push_commit", "fake-commit", "KiPilot MCP: sch_set_page_settings"),
    ]


async def test_set_schematic_title_block_dry_run_previews_merged_changes() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.set_schematic_title_block(
        title="Updated Schematic",
        comments={2: "Released", "3": "Customer"},
        dry_run=True,
    )

    assert result == {
        "ok": True,
        "mutation": "sch_set_title_block",
        "dry_run": True,
        "commit_message": None,
        "schematic": {
            "name": "demo.kicad_sch",
            "document": {
                "type": "2",
                "board_filename": "",
                "project": {
                    "name": "demo",
                    "path": "C:/demo/demo.kicad_pro",
                },
                "path": "C:/demo/demo.kicad_sch",
            },
        },
        "previous_title_block": {
            "title": "Demo Schematic",
            "revision": "A",
            "date": "2026-05-19",
            "company": "KiPilot Labs",
            "comments": {
                "1": "Main sheet",
                "2": "Internal",
            },
        },
        "title_block": {
            "title": "Updated Schematic",
            "revision": "A",
            "date": "2026-05-19",
            "company": "KiPilot Labs",
            "comments": {
                "1": "Main sheet",
                "2": "Released",
                "3": "Customer",
            },
        },
        "requested_changes": {
            "title": "Updated Schematic",
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
    assert FakeMutationKiCad.last_instance.schematic.calls == []


async def test_set_schematic_title_block_updates_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.set_schematic_title_block(revision="B", company="KiPilot Systems")

    assert result["ok"] is True
    assert result["mutation"] == "sch_set_title_block"
    assert result["title_block"] == {
        "title": "Demo Schematic",
        "revision": "B",
        "date": "2026-05-19",
        "company": "KiPilot Systems",
        "comments": {
            "1": "Main sheet",
            "2": "Internal",
        },
    }
    assert FakeMutationKiCad.last_instance is not None
    assert FakeMutationKiCad.last_instance.schematic.calls == [
        ("begin_commit",),
        (
            "set_title_block",
            "Demo Schematic",
            "B",
            "2026-05-19",
            "KiPilot Systems",
            {1: "Main sheet", 2: "Internal"},
        ),
        ("push_commit", "fake-commit", "KiPilot MCP: sch_set_title_block"),
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
                "layer": "B.Cu",
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
    assert result["updates"][0]["item"]["layer"] == 31
    assert result["updates"][0]["requested_changes"]["layer"] == {"id": 31, "name": "B.Cu"}
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


async def test_update_items_footprint_layer_change_flips_orientation() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=False), kicad_factory=FakeMutationKiCad)

    result = await client.update_items(
        updates=[
            {
                "kind": "footprint",
                "reference": "R1",
                "layer": "B.Cu",
            }
        ],
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["updates"][0]["item"]["layer"] == 31
    assert result["updates"][0]["item"]["orientation"] == "-90deg"


async def test_update_items_updates_multiple_items_when_enabled() -> None:
    client = KiCadIpcClient(KiCadIpcConfig(enable_mutations=True), kicad_factory=FakeMutationKiCad)

    result = await client.update_items(
        updates=[
            {
                "kind": "footprint",
                "footprint_id": "footprint-id",
                "orientation_degrees": 45,
                "layer": 31,
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
    assert result["updates"][0]["item"]["layer"] == 31
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


class FakeSchematicKiCad:
    last_instance: FakeSchematicKiCad | None = None

    def __init__(self, **_kwargs: object) -> None:
        self.schematic = FakeSchematic()
        type(self).last_instance = self

    def get_schematic(self) -> FakeSchematic:
        return self.schematic

    def close(self) -> None:
        pass


class FakeMutationKiCad(FakeBoardKiCad):
    last_instance: FakeMutationKiCad | None = None

    def __init__(self, **_kwargs: object) -> None:
        self.board = FakeMutationBoard()
        self.schematic = FakeMutationSchematic()
        FakeMutationKiCad.last_instance = self

    def get_board(self) -> FakeMutationBoard:
        return self.board

    def get_schematic(self) -> FakeMutationSchematic:
        return self.schematic

    def get_text_extents(self, text: object) -> FakeBox:
        box_getter = getattr(text, "bounding_box", None)
        if callable(box_getter):
            return box_getter()
        raise AssertionError("text input does not provide bounding_box()")

    def get_text_as_shapes(self, texts: object | list[object]) -> list[FakeCompoundShape]:
        resolved_texts = texts if isinstance(texts, list) else [texts]
        result = []
        for text in resolved_texts:
            box = self.get_text_extents(text)
            result.append(
                FakeCompoundShape(
                    [
                        FakeShape(
                            f"{getattr(text, 'id', 'text')}-shape",
                            getattr(text, "layer", 37),
                            box.top_left,
                            box.bottom_right,
                        )
                    ]
                )
            )
        return result


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

    def get_dimensions(self) -> list[FakeDimension]:
        return [FakeDimension()]

    def get_groups(self) -> list[FakeGroup]:
        return [FakeGroup()]

    def get_reference_images(self) -> list[FakeReferenceImage]:
        return [FakeReferenceImage()]

    def get_barcodes(self) -> list[FakeBarcode]:
        return [FakeBarcode()]

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


class FakePowerNet:
    name = "12V"
    code = 12


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


class FakeMutationProject(FakeProject):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._text_variables = {
            "BOARD_REV": "A",
            "AUTHOR": "KiPilot",
        }

    def get_text_variables(self) -> dict[str, str]:
        return dict(self._text_variables)

    def expand_text_variables(self, text: str) -> str:
        expanded = text
        for key, value in self._text_variables.items():
            expanded = expanded.replace(f"${{{key}}}", value)
        return expanded

    def set_text_variables(self, variables: object, merge_mode: int = 1) -> None:
        if isinstance(variables, dict):
            resolved = {str(key): str(value) for key, value in variables.items()}
        elif hasattr(variables, "items"):
            resolved = {str(key): str(value) for key, value in variables.items()}
        elif hasattr(variables, "variables"):
            resolved = {str(key): str(value) for key, value in dict(variables.variables).items()}
        else:
            resolved = {}

        self.calls.append(("set_text_variables", dict(resolved), merge_mode))
        if merge_mode == 2:
            self._text_variables = dict(resolved)
        else:
            self._text_variables.update(resolved)


class FakeGraphicsTextAttributes:
    def __init__(
        self,
        *,
        font_name: str,
        angle: float,
        line_spacing: float,
        stroke_width: int,
        italic: bool,
        bold: bool,
        underlined: bool,
        mirrored: bool,
        multiline: bool,
        keep_upright: bool,
        size: FakeVector,
        horizontal_alignment: int,
        vertical_alignment: int,
    ) -> None:
        self.font_name = font_name
        self.angle = angle
        self.line_spacing = line_spacing
        self.stroke_width = stroke_width
        self.italic = italic
        self.bold = bold
        self.underlined = underlined
        self.mirrored = mirrored
        self.multiline = multiline
        self.keep_upright = keep_upright
        self.size = size
        self.horizontal_alignment = horizontal_alignment
        self.vertical_alignment = vertical_alignment


class FakeGraphicsDefault:
    def __init__(self, *, layer: int, line_thickness: int, text: FakeGraphicsTextAttributes) -> None:
        self.layer = layer
        self.line_thickness = line_thickness
        self.text = text


class FakeEditorAppearanceSettings:
    def __init__(
        self,
        other: "FakeEditorAppearanceSettings | None" = None,
        *,
        inactive_layer_display: int = 1,
        net_color_display: int = 2,
        board_flip: int = 1,
        ratsnest_display: int = 3,
    ) -> None:
        if other is not None:
            self.inactive_layer_display = other.inactive_layer_display
            self.net_color_display = other.net_color_display
            self.board_flip = other.board_flip
            self.ratsnest_display = other.ratsnest_display
            return

        self.inactive_layer_display = inactive_layer_display
        self.net_color_display = net_color_display
        self.board_flip = board_flip
        self.ratsnest_display = ratsnest_display


class FakeCompoundShape:
    def __init__(self, shapes: list[object]) -> None:
        self.shapes = list(shapes)


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


class FakeJobResult:
    def __init__(self, *, output_path: str, message: str) -> None:
        self.succeeded = True
        self.status = 1
        self.output_paths = [output_path]
        self.message = message


class FakePageSettings:
    def __init__(
        self,
        proto: FakePageSettings | None = None,
        *,
        page_size: int = 5,
        orientation: int = 1,
        drawing_sheet: str = "A4.kicad_wks",
        user_page_size: FakeVector | None = None,
    ) -> None:
        if proto is not None:
            page_size = proto.page_size
            orientation = proto.orientation
            drawing_sheet = proto.drawing_sheet
            user_page_size = FakeVector(proto.user_page_size.x, proto.user_page_size.y)

        self.page_size = page_size
        self.orientation = orientation
        self.drawing_sheet = drawing_sheet
        self.user_page_size = user_page_size or FakeVector(210_000_000, 297_000_000)
        self.proto = self


class FakeSchematicPlotSettings:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        values = dict(values or {})
        self.drawing_sheet = str(values.get("drawing_sheet", ""))
        self.default_font = str(values.get("default_font", ""))
        self.variant = str(values.get("variant", ""))
        self.plot_all = bool(values.get("plot_all", False))
        self.plot_drawing_sheet = bool(values.get("plot_drawing_sheet", False))
        self.plot_pages = list(values.get("plot_pages", []))
        self.show_hop_over = bool(values.get("show_hop_over", False))
        self.black_and_white = bool(values.get("black_and_white", False))
        self.page_size = int(values.get("page_size", 0))
        self.use_background_color = bool(values.get("use_background_color", False))
        self.min_pen_width = int(values.get("min_pen_width", 0))
        self.theme = str(values.get("theme", ""))
        self.proto = self
        self.proto = self


class FakeSchematicBomFormatSettings:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        values = dict(values or {})
        self.preset_name = str(values.get("preset_name", ""))
        self.field_delimiter = str(values.get("field_delimiter", ""))
        self.string_delimiter = str(values.get("string_delimiter", ""))
        self.ref_delimiter = str(values.get("ref_delimiter", ""))
        self.ref_range_delimiter = str(values.get("ref_range_delimiter", ""))
        self.keep_tabs = bool(values.get("keep_tabs", False))
        self.keep_line_breaks = bool(values.get("keep_line_breaks", False))
        self.proto = self

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakeSchematicBomFormatSettings) and (
            self.preset_name,
            self.field_delimiter,
            self.string_delimiter,
            self.ref_delimiter,
            self.ref_range_delimiter,
            self.keep_tabs,
            self.keep_line_breaks,
        ) == (
            other.preset_name,
            other.field_delimiter,
            other.string_delimiter,
            other.ref_delimiter,
            other.ref_range_delimiter,
            other.keep_tabs,
            other.keep_line_breaks,
        )


class FakeSchematicBomField:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        values = dict(values or {})
        self.name = str(values.get("name", ""))
        self.label = str(values.get("label", ""))
        self.group_by = bool(values.get("group_by", False))
        self.proto = self

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakeSchematicBomField) and (
            self.name,
            self.label,
            self.group_by,
        ) == (
            other.name,
            other.label,
            other.group_by,
        )


class FakeSchematicBomFieldSettings:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        values = dict(values or {})
        self.preset_name = str(values.get("preset_name", ""))
        self.fields = [FakeSchematicBomField(field) for field in values.get("fields", [])]
        self.sort_field = str(values.get("sort_field", ""))
        self.sort_direction = int(values.get("sort_direction", 0))
        self.filter = str(values.get("filter", ""))
        self.proto = self

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakeSchematicBomFieldSettings) and (
            self.preset_name,
            self.fields,
            self.sort_field,
            self.sort_direction,
            self.filter,
        ) == (
            other.preset_name,
            other.fields,
            other.sort_field,
            other.sort_direction,
            other.filter,
        )


class FakeSheetPath:
    def __init__(
        self,
        path: list[str],
        path_human_readable: str = "",
    ) -> None:
        self.path = list(path)
        self.path_human_readable = path_human_readable


class FakeSheetInstance:
    def __init__(
        self,
        *,
        name: str,
        filename: str,
        page_number: str,
        path: FakeSheetPath,
        children: list[FakeSheetInstance] | None = None,
    ) -> None:
        self.name = name
        self.filename = filename
        self.page_number = page_number
        self.path = path
        self.children = list(children or [])


class FakeSchematicNetSheetContents:
    def __init__(self, *, path: FakeSheetPath, items: list[str]) -> None:
        self.path = path
        self.items = list(items)


class FakeSchematicNet:
    def __init__(self, *, name: str, sheets: list[FakeSchematicNetSheetContents]) -> None:
        self.name = name
        self.sheets = list(sheets)


class FakeSchematicLookupItem:
    def __init__(self, item_id: str, top_left: FakeVector, bottom_right: FakeVector) -> None:
        self.id = item_id
        self._top_left = top_left
        self._bottom_right = bottom_right

    def bounding_box(self) -> FakeBox:
        return FakeBox(self._top_left, self._bottom_right)


class FakeSchematic:
    name = "demo.kicad_sch"
    document = type(
        "FakeSchematicDocument",
        (),
        {
            "type": 2,
            "project": type(
                "FakeSchematicProjectRef",
                (),
                {"name": "demo", "path": "C:/demo/demo.kicad_pro"},
            )(),
            "path": "C:/demo/demo.kicad_sch",
        },
    )()

    def get_hierarchy(self) -> list[FakeSheetInstance]:
        return [
            FakeSheetInstance(
                name="Root",
                filename="demo.kicad_sch",
                page_number="1",
                path=FakeSheetPath(["root-sheet"], "/Root"),
                children=[
                    FakeSheetInstance(
                        name="Power",
                        filename="power.kicad_sch",
                        page_number="2",
                        path=FakeSheetPath(["root-sheet", "power-sheet"], "/Root/Power"),
                    )
                ],
            )
        ]

    def get_netlist(self, types: object | None = None) -> list[FakeSchematicNet]:
        if types == [1001]:
            return [
                FakeSchematicNet(
                    name="+3V3",
                    sheets=[
                        FakeSchematicNetSheetContents(
                            path=FakeSheetPath(["root-sheet"], "/Root"),
                            items=["symbol-1", "label-1"],
                        )
                    ],
                )
            ]

        return [
            FakeSchematicNet(
                name="+3V3",
                sheets=[
                    FakeSchematicNetSheetContents(
                        path=FakeSheetPath(["root-sheet"], "/Root"),
                        items=["symbol-1", "label-1"],
                    )
                ],
            ),
            FakeSchematicNet(
                name="GND",
                sheets=[
                    FakeSchematicNetSheetContents(
                        path=FakeSheetPath(["root-sheet", "power-sheet"], "/Root/Power"),
                        items=["symbol-2", "label-2"],
                    )
                ],
            ),
        ]

    def get_page_settings(self) -> FakePageSettings:
        return FakePageSettings()

    def get_title_block(self) -> FakeTitleBlock:
        return FakeTitleBlock(
            title="Demo Schematic",
            revision="A",
            date="2026-05-19",
            company="KiPilot Labs",
            comments={1: "Main sheet", 2: "Internal"},
        )

    def __init__(self) -> None:
        self.last_export_netlist_call: dict[str, object] | None = None
        self.last_export_bom_call: dict[str, object] | None = None
        self._items_by_id = {
            "symbol-1": FakeSchematicLookupItem(
                "symbol-1",
                FakeVector(1_000_000, 1_000_000),
                FakeVector(5_000_000, 4_000_000),
            )
        }

    def get_items_by_id(self, ids: object | list[object]) -> list[FakeSchematicLookupItem]:
        resolved_ids = ids if isinstance(ids, list) else [ids]
        result = []
        for item_id in resolved_ids:
            normalized_item_id = str(getattr(item_id, "value", item_id)).strip().lower()
            item = self._items_by_id.get(normalized_item_id)
            if item is not None:
                result.append(item)
        return result

    def hit_test(self, item: object, position: FakeVector, tolerance: int = 0) -> bool:
        box_getter = getattr(item, "bounding_box", None)
        if not callable(box_getter):
            return False

        bounding_box = box_getter()
        return (
            bounding_box.top_left.x - tolerance <= position.x <= bounding_box.bottom_right.x + tolerance
            and bounding_box.top_left.y - tolerance <= position.y <= bounding_box.bottom_right.y + tolerance
        )

    def export_svg(self, output_path: str, plot_settings: object | None = None) -> FakeJobResult:
        return FakeJobResult(output_path=output_path, message="SVG export completed.")

    def export_dxf(self, output_path: str, plot_settings: object | None = None) -> FakeJobResult:
        return FakeJobResult(output_path=output_path, message="DXF export completed.")

    def export_pdf(
        self,
        output_path: str,
        plot_settings: object | None = None,
        *,
        property_popups: bool = False,
        hierarchical_links: bool = False,
        include_metadata: bool = True,
    ) -> FakeJobResult:
        return FakeJobResult(output_path=output_path, message="PDF export completed.")

    def export_ps(self, output_path: str, plot_settings: object | None = None) -> FakeJobResult:
        return FakeJobResult(output_path=output_path, message="PS export completed.")

    def export_netlist(
        self,
        output_path: str,
        format: int = 2,
        variant_name: str = "",
    ) -> FakeJobResult:
        self.last_export_netlist_call = {
            "output_path": output_path,
            "format": format,
            "variant_name": variant_name,
        }
        return FakeJobResult(output_path=output_path, message="Netlist export completed.")

    def export_bom(
        self,
        output_path: str,
        format_settings: object | None = None,
        field_settings: object | None = None,
        *,
        exclude_dnp: bool = False,
        group_symbols: bool = False,
        variant_name: str = "",
    ) -> FakeJobResult:
        self.last_export_bom_call = {
            "output_path": output_path,
            "format_settings": format_settings,
            "field_settings": field_settings,
            "exclude_dnp": exclude_dnp,
            "group_symbols": group_symbols,
            "variant_name": variant_name,
        }
        return FakeJobResult(output_path=output_path, message="BOM export completed.")


class FakeSchematicWithoutExports(FakeSchematic):
    export_svg = None
    export_dxf = None
    export_pdf = None
    export_ps = None
    export_netlist = None
    export_bom = None


class FakeSchematicWithoutHitTest(FakeSchematic):
    hit_test = None


class FakeMutationSchematic(FakeSchematic):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._page_settings = FakePageSettings()
        self._title_block = FakeTitleBlock(
            title="Demo Schematic",
            revision="A",
            date="2026-05-19",
            company="KiPilot Labs",
            comments={1: "Main sheet", 2: "Internal"},
        )

    def begin_commit(self) -> str:
        self.calls.append(("begin_commit",))
        return "fake-commit"

    def push_commit(self, commit: str, message: str = "") -> None:
        self.calls.append(("push_commit", commit, message))

    def drop_commit(self, commit: str) -> None:
        self.calls.append(("drop_commit", commit))

    def get_page_settings(self) -> FakePageSettings:
        return FakePageSettings(self._page_settings)

    def set_page_settings(self, page_settings: FakePageSettings) -> FakePageSettings:
        self.calls.append(
            (
                "set_page_settings",
                page_settings.page_size,
                page_settings.orientation,
                page_settings.drawing_sheet,
                page_settings.user_page_size.x,
                page_settings.user_page_size.y,
            )
        )
        self._page_settings = FakePageSettings(page_settings)
        return FakePageSettings(self._page_settings)

    def get_title_block(self) -> FakeTitleBlock:
        return FakeTitleBlock(self._title_block)

    def set_title_block(self, title_block: FakeTitleBlock) -> None:
        self.calls.append(
            (
                "set_title_block",
                title_block.title,
                title_block.revision,
                title_block.date,
                title_block.company,
                dict(title_block.comments),
            )
        )
        self._title_block = FakeTitleBlock(title_block)


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


class FakeDimension:
    id = "dimension-id"
    layer = 44
    locked = False
    text = type("FakeDimensionText", (), {"value": "12.34 mm"})()
    override_text_enabled = False
    start = FakeVector(1_000_000, 1_000_000)
    end = FakeVector(5_000_000, 3_000_000)
    height = 1_000_000
    extension_height = 500_000

    def bounding_box(self) -> FakeBox:
        return FakeBox(self.start, self.end)


class FakeGroup:
    id = "group-id"
    name = "Placement cluster"
    items = [FakeTrack(), type("FakeGroupMember", (), {"id": "shape-silk-1"})()]


class FakeReferenceImage:
    id = "reference-image-id"
    layer = 37
    locked = False
    position = FakeVector(15_000_000, 5_000_000)
    transform_origin_offset = FakeVector(500_000, 250_000)
    image_scale = 0.5
    image_data = b"PNGDATA"

    def bounding_box(self) -> FakeBox:
        return FakeBox(self.position, FakeVector(17_000_000, 6_500_000))


class FakeBarcode:
    id = "barcode-id"
    text = "SN0001"
    kind = "qr"
    error_correction = "M"
    position = FakeVector(25_000_000, 12_000_000)
    orientation = FakeAngle(90)
    layer = 37
    width = 6_000_000
    height = 6_000_000
    show_text = True
    text_height = 1_200_000
    knockout = False
    knockout_margin = FakeVector(200_000, 200_000)
    locked = False

    def bounding_box(self) -> FakeBox:
        return FakeBox(self.position, FakeVector(31_000_000, 18_000_000))


class FakeMutationBoard(FakeBoard):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._project = FakeMutationProject()
        self._next_created_item_id = 1
        self._selection_ids = ["track-id"]
        self._graphics_defaults = {
            1: FakeGraphicsDefault(
                layer=1,
                line_thickness=150_000,
                text=FakeGraphicsTextAttributes(
                    font_name="KiCad Font",
                    angle=0.0,
                    line_spacing=1.0,
                    stroke_width=120_000,
                    italic=False,
                    bold=False,
                    underlined=False,
                    mirrored=False,
                    multiline=False,
                    keep_upright=True,
                    size=FakeVector(1_000_000, 1_200_000),
                    horizontal_alignment=1,
                    vertical_alignment=2,
                ),
            ),
            2: FakeGraphicsDefault(
                layer=2,
                line_thickness=200_000,
                text=FakeGraphicsTextAttributes(
                    font_name="KiCad Sans",
                    angle=90.0,
                    line_spacing=1.1,
                    stroke_width=180_000,
                    italic=True,
                    bold=True,
                    underlined=False,
                    mirrored=False,
                    multiline=True,
                    keep_upright=False,
                    size=FakeVector(1_500_000, 1_500_000),
                    horizontal_alignment=2,
                    vertical_alignment=3,
                ),
            ),
        }
        self._editor_appearance_settings = FakeEditorAppearanceSettings()
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

    def get_project(self) -> FakeMutationProject:
        return self._project

    def get_selection(self) -> list[object]:
        return [item for item in self._all_items() if getattr(item, "id", "") in self._selection_ids]

    def get_graphics_defaults(self) -> dict[int, FakeGraphicsDefault]:
        return dict(self._graphics_defaults)

    def get_editor_appearance_settings(self) -> FakeEditorAppearanceSettings:
        return FakeEditorAppearanceSettings(self._editor_appearance_settings)

    def set_editor_appearance_settings(self, settings: FakeEditorAppearanceSettings) -> None:
        self.calls.append(
            (
                "set_editor_appearance_settings",
                settings.inactive_layer_display,
                settings.net_color_display,
                settings.board_flip,
                settings.ratsnest_display,
            )
        )
        self._editor_appearance_settings = FakeEditorAppearanceSettings(settings)

    def hit_test(self, item: object, position: FakeVector, tolerance: int = 0) -> bool:
        box_getter = getattr(item, "bounding_box", None)
        if not callable(box_getter):
            return False

        bounding_box = box_getter()
        return (
            bounding_box.top_left.x - tolerance <= position.x <= bounding_box.bottom_right.x + tolerance
            and bounding_box.top_left.y - tolerance <= position.y <= bounding_box.bottom_right.y + tolerance
        )

    def check_padstack_presence_on_layers(
        self,
        items: object | list[object],
        layers: int | list[int],
    ) -> dict[object, dict[int, bool]]:
        resolved_items = items if isinstance(items, list) else [items]
        resolved_layers = layers if isinstance(layers, list) else [layers]
        result: dict[object, dict[int, bool]] = {}
        for item in resolved_items:
            padstack_layers = list(getattr(getattr(item, "padstack", None), "layers", []))
            result[item] = {int(layer): int(layer) in padstack_layers for layer in resolved_layers}
        return result

    def get_pad_shapes_as_polygons(
        self,
        pads: object | list[object],
        layer: int = 0,
    ) -> list[FakeMutablePolygon]:
        resolved_pads = pads if isinstance(pads, list) else [pads]
        polygons = []
        for pad in resolved_pads:
            if layer not in list(getattr(getattr(pad, "padstack", None), "layers", [])):
                continue
            position = getattr(pad, "position", FakeVector(0, 0))
            polygons.append(
                FakeMutablePolygon(
                    outline=[
                        FakeVector(position.x - 250_000, position.y - 250_000),
                        FakeVector(position.x + 250_000, position.y - 250_000),
                        FakeVector(position.x + 250_000, position.y + 250_000),
                        FakeVector(position.x - 250_000, position.y + 250_000),
                    ]
                )
            )
        return polygons

    def add_to_selection(self, items: object | list[object]) -> list[object]:
        resolved_items = items if isinstance(items, list) else [items]
        item_ids = [str(getattr(item, "id", "")) for item in resolved_items]
        self.calls.append(("add_to_selection", item_ids))
        for item_id in item_ids:
            if item_id and item_id not in self._selection_ids:
                self._selection_ids.append(item_id)
        return self.get_selection()

    def remove_from_selection(self, items: object | list[object]) -> list[object]:
        resolved_items = items if isinstance(items, list) else [items]
        item_ids = [str(getattr(item, "id", "")) for item in resolved_items]
        self.calls.append(("remove_from_selection", item_ids))
        self._selection_ids = [item_id for item_id in self._selection_ids if item_id not in item_ids]
        return self.get_selection()

    def clear_selection(self) -> None:
        self.calls.append(("clear_selection",))
        self._selection_ids = []

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

    def _all_items(self) -> list[object]:
        return [
            *self._footprints,
            *self._tracks,
            *self._vias,
            *self._zones,
            *self._text_items,
        ]

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

    def save_as(self, filename: str, overwrite: bool = False, include_project: bool = True) -> None:
        self.calls.append(("save_as", filename, overwrite, include_project))

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
        definition_items: list[object] | None = None,
    ) -> None:
        reference_field = None
        value_field = None
        datasheet_field = None
        description_field = None
        if proto is not None:
            footprint_id = proto.id
            reference = str(proto.reference_field.text.value)
            value = str(proto.value_field.text.value)
            position = FakeVector(proto.position.x, proto.position.y)
            orientation = FakeAngle(proto.orientation.degrees)
            layer = proto.layer
            locked = proto.locked
            reference_field = getattr(proto, "reference_field", None)
            value_field = getattr(proto, "value_field", None)
            datasheet_field = getattr(proto, "datasheet_field", None)
            description_field = getattr(proto, "description_field", None)
            definition_items = [
                _clone_fake_wrapper(item)
                for item in getattr(getattr(proto, "definition", None), "items", [])
            ]

        self.id = footprint_id
        self.reference_field = _make_fake_field(reference, proto=reference_field)
        self.value_field = _make_fake_field(value, proto=value_field)
        self.datasheet_field = _make_fake_field(proto=datasheet_field)
        self.description_field = _make_fake_field(proto=description_field)
        self.position = position or FakeVector(0, 0)
        self.orientation = orientation or FakeAngle(0)
        self.layer = layer
        self.locked = locked
        self.definition = FakeFootprintDefinition(items=definition_items)
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


class FakeMutablePadStack:
    def __init__(self, proto: FakeMutablePadStack | None = None, *, layers: list[int] | None = None) -> None:
        if proto is not None:
            layers = list(getattr(proto, "layers", [0]))

        self.layers = list(layers or [0])
        self.proto = self


class FakeMutablePad:
    def __init__(
        self,
        proto: FakeMutablePad | None = None,
        *,
        pad_id: str = "pad-id",
        number: str = "1",
        position: FakeVector | None = None,
        net: object | None = None,
        pad_type: str = "thru_hole",
        padstack: FakeMutablePadStack | None = None,
    ) -> None:
        if proto is not None:
            pad_id = str(getattr(proto, "id", "pad-id"))
            number = str(getattr(proto, "number", "1"))
            position = _clone_vector(getattr(proto, "position", None))
            net = getattr(proto, "net", None)
            pad_type = str(getattr(proto, "pad_type", "thru_hole"))
            padstack = FakeMutablePadStack(getattr(proto, "padstack", None))

        self.id = pad_id
        self.number = number
        self.position = position or FakeVector(0, 0)
        self.net = net
        self.pad_type = pad_type
        self.padstack = padstack or FakeMutablePadStack()
        self.proto = self


class FakeMutablePolygon:
    def __init__(
        self,
        proto: FakeMutablePolygon | None = None,
        *,
        outline: list[FakeVector] | None = None,
        holes: list[list[FakeVector]] | None = None,
    ) -> None:
        if proto is not None:
            outline = [
                cloned
                for point in getattr(proto, "outline", [])
                if (cloned := _clone_vector(point)) is not None
            ]
            holes = [
                [cloned for point in hole if (cloned := _clone_vector(point)) is not None]
                for hole in getattr(proto, "holes", [])
            ]

        self.outline = list(outline or [])
        self.holes = [list(hole) for hole in holes or []]
        self.proto = self


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
        mirrored: bool = False,
    ) -> None:
        if proto is not None:
            angle = proto.angle
            mirrored = getattr(proto, "mirrored", mirrored)

        self.angle = float(angle)
        self.mirrored = bool(mirrored)
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

    def as_text(self) -> FakeMutableBoardText:
        return self

    def bounding_box(self) -> FakeBox:
        width = max(len(self.value), 1) * 500_000
        return FakeBox(
            self.position,
            FakeVector(self.position.x + width, self.position.y + 1_000_000),
        )


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

    def as_textbox(self) -> FakeMutableBoardTextBox:
        return self

    def bounding_box(self) -> FakeBox:
        return FakeBox(self.top_left, self.bottom_right)


class FakeMutableBoardPolygon:
    def __init__(
        self,
        proto: FakeMutableBoardPolygon | None = None,
        *,
        shape_id: str = "board-polygon-id",
        layer: int = 37,
        polygons: list[FakeMutablePolygon] | None = None,
        locked: bool = False,
    ) -> None:
        if proto is not None:
            shape_id = str(getattr(proto, "id", shape_id))
            layer = getattr(proto, "layer", layer)
            polygons = [FakeMutablePolygon(polygon) for polygon in getattr(proto, "polygons", [])]
            locked = getattr(proto, "locked", locked)

        self.id = shape_id
        self.layer = layer
        self.polygons = list(polygons or [])
        self.locked = locked
        self.proto = self


class FakeFootprintDefinition:
    def __init__(
        self,
        proto: FakeFootprintDefinition | None = None,
        *,
        items: list[object] | None = None,
    ) -> None:
        if proto is not None:
            items = [_clone_fake_wrapper(item) for item in getattr(proto, "items", [])]

        self.items = list(items or [])
        self.proto = self


def _make_fake_field(
    value: str = "",
    proto: object | None = None,
    *,
    layer: int = 37,
    position: FakeVector | None = None,
    angle: float = 0.0,
    mirrored: bool = False,
) -> object:
    attributes = FakeTextAttributes(angle=angle, mirrored=mirrored)
    visible = True
    if proto is not None:
        text = getattr(proto, "text", None)
        value = str(getattr(text, "value", value))
        layer = getattr(text, "layer", layer)
        position = _clone_vector(getattr(text, "position", None))
        attributes = FakeTextAttributes(getattr(text, "attributes", None))
        visible = bool(getattr(proto, "visible", visible))

    field = type("FakeField", (), {})()
    field.text = FakeMutableBoardText(
        value=value,
        layer=layer,
        position=position,
        attributes=attributes,
    )
    field.visible = visible
    field.proto = field
    return field


def _clone_fake_wrapper(value: object) -> object:
    proto = getattr(value, "proto", value)
    try:
        return type(value)(proto)
    except Exception:
        return value


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
