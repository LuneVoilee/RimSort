from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.models.collections import CollectionStore


class DummySettingsController:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            current_instance="Default",
            instances={"Default": SimpleNamespace(instance_folder_override="")},
        )


def test_collection_store_crud(monkeypatch: object, tmp_path: Path) -> None:
    from app.models import collections as collections_module

    monkeypatch.setattr(  # type: ignore[attr-defined]
        collections_module.InstanceController,
        "get_instance_folder_path",
        staticmethod(lambda instance_name, override_path="": tmp_path),
    )
    store = CollectionStore(DummySettingsController())  # type: ignore[arg-type]

    collections, created = store.create_collection("Test Collection")
    assert collections is not None
    assert created is not None
    assert created.name == "Test Collection"
    assert created.color == "#00007f"
    assert created.cover_type == "auto"
    assert created.cover_image_path == ""
    assert created.cover_package_id == ""

    updated = store.add_package_ids(created.id, ["A.Mod", "a.mod", "B.Mod"])
    assert updated is not None
    modified = next(entry for entry in updated if entry.id == created.id)
    assert modified.package_ids == ["a.mod", "b.mod"]

    modified.cover_type = "file"
    modified.cover_image_path = str(tmp_path / "cover.png")
    modified.cover_package_id = "a.mod"
    updated_cover = store.update_collection(modified)
    assert updated_cover is not None
    modified = next(entry for entry in updated_cover if entry.id == created.id)
    assert modified.cover_type == "file"
    assert modified.cover_image_path == str(tmp_path / "cover.png")
    assert modified.cover_package_id == ""

    modified.cover_type = "package"
    modified.cover_image_path = ""
    modified.cover_package_id = "a.mod"
    updated_cover = store.update_collection(modified)
    assert updated_cover is not None
    modified = next(entry for entry in updated_cover if entry.id == created.id)
    assert modified.cover_type == "package"
    assert modified.cover_image_path == ""
    assert modified.cover_package_id == "a.mod"

    reordered = store.set_package_ids(created.id, ["b.mod", "a.mod", "b.mod"])
    assert reordered is not None
    modified = next(entry for entry in reordered if entry.id == created.id)
    assert modified.package_ids == ["b.mod", "a.mod"]
    assert modified.cover_type == "package"
    assert modified.cover_package_id == "a.mod"

    trimmed = store.remove_package_ids(created.id, ["a.mod"])
    assert trimmed is not None
    modified = next(entry for entry in trimmed if entry.id == created.id)
    assert modified.package_ids == ["b.mod"]
    assert modified.cover_type == "auto"
    assert modified.cover_image_path == ""
    assert modified.cover_package_id == ""

    remaining = store.delete_collection(created.id)
    assert remaining == []
