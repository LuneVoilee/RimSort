from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger

from app.controllers.instance_controller import InstanceController
from app.controllers.settings_controller import SettingsController

DEFAULT_COLLECTION_COLOR = "#00007f"
BACKGROUND_COLOR = "#101820"
COLLECTION_COVER_TYPE_AUTO = "auto"
COLLECTION_COVER_TYPE_FILE = "file"
COLLECTION_COVER_TYPE_PACKAGE = "package"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_package_id(package_id: str) -> str:
    return package_id.strip().lower()


def _normalize_collection_color(color: Any) -> str:
    if not isinstance(color, str):
        return DEFAULT_COLLECTION_COLOR
    normalized = color.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", normalized):
        return normalized
    return DEFAULT_COLLECTION_COLOR


def _normalize_collection_cover_type(cover_type: Any) -> str:
    if not isinstance(cover_type, str):
        return COLLECTION_COVER_TYPE_AUTO
    normalized = cover_type.strip().lower()
    if normalized in (
        COLLECTION_COVER_TYPE_AUTO,
        COLLECTION_COVER_TYPE_FILE,
        COLLECTION_COVER_TYPE_PACKAGE,
    ):
        return normalized
    return COLLECTION_COVER_TYPE_AUTO


def _normalize_collection_cover_settings(
    cover_type: Any,
    cover_image_path: Any,
    cover_package_id: Any,
    package_ids: list[str],
) -> tuple[str, str, str]:
    normalized_cover_type = _normalize_collection_cover_type(cover_type)
    normalized_cover_image_path = (
        cover_image_path.strip() if isinstance(cover_image_path, str) else ""
    )
    normalized_cover_package_id = (
        _normalize_package_id(cover_package_id) if isinstance(cover_package_id, str) else ""
    )

    if normalized_cover_type == COLLECTION_COVER_TYPE_FILE:
        if normalized_cover_image_path:
            return normalized_cover_type, normalized_cover_image_path, ""
        return COLLECTION_COVER_TYPE_AUTO, "", ""

    if normalized_cover_type == COLLECTION_COVER_TYPE_PACKAGE:
        if (
            normalized_cover_package_id
            and normalized_cover_package_id in set(package_ids)
        ):
            return normalized_cover_type, "", normalized_cover_package_id
        return COLLECTION_COVER_TYPE_AUTO, "", ""

    return COLLECTION_COVER_TYPE_AUTO, "", ""


@dataclass
class Collection:
    id: str
    name: str
    description: str = ""
    color: str = DEFAULT_COLLECTION_COLOR
    cover_type: str = COLLECTION_COVER_TYPE_AUTO
    cover_image_path: str = ""
    cover_package_id: str = ""
    package_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    @staticmethod
    def create(
            name: str,
            description: str = "",
            color: str = DEFAULT_COLLECTION_COLOR,
    ) -> "Collection":
        now = _utc_now_iso()
        return Collection(
            id=uuid4().hex,
            name=name.strip(),
            description=description.strip(),
            color=_normalize_collection_color(color),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "Collection":
        raw_package_ids = raw.get("package_ids", [])
        package_ids: list[str] = []
        if isinstance(raw_package_ids, list):
            seen: set[str] = set()
            for package_id in raw_package_ids:
                if not isinstance(package_id, str):
                    continue
                normalized = _normalize_package_id(package_id)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    package_ids.append(normalized)
        cover_type, cover_image_path, cover_package_id = (
            _normalize_collection_cover_settings(
                raw.get("cover_type"),
                raw.get("cover_image_path"),
                raw.get("cover_package_id"),
                package_ids,
            )
        )
        return Collection(
            id=str(raw.get("id", uuid4().hex)),
            name=str(raw.get("name", "Untitled Collection")).strip(),
            description=str(raw.get("description", "")).strip(),
            color=_normalize_collection_color(raw.get("color", DEFAULT_COLLECTION_COLOR)),
            cover_type=cover_type,
            cover_image_path=cover_image_path,
            cover_package_id=cover_package_id,
            package_ids=package_ids,
            created_at=str(raw.get("created_at", _utc_now_iso())),
            updated_at=str(raw.get("updated_at", _utc_now_iso())),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CollectionStore:
    FILE_NAME = "collections.json"

    def __init__(self, settings_controller: SettingsController) -> None:
        self.settings_controller = settings_controller

    def _instance_collections_file(self) -> Path:
        current_instance_name = self.settings_controller.settings.current_instance
        current_instance = self.settings_controller.settings.instances[
            current_instance_name
        ]
        instance_folder_override = getattr(current_instance, "instance_folder_override", "")
        instance_path = InstanceController.get_instance_folder_path(
            current_instance_name, instance_folder_override
        )
        return instance_path / self.FILE_NAME

    def load(self) -> list[Collection]:
        file_path = self._instance_collections_file()
        if not file_path.exists():
            return []

        try:
            with open(file_path, encoding="utf-8") as stream:
                raw = json.load(stream)
        except Exception as error:
            logger.error(f"Failed to read collections file {file_path}: {error}")
            return []

        collections_raw = raw.get("collections", []) if isinstance(raw, dict) else []
        if not isinstance(collections_raw, list):
            return []
        return [Collection.from_dict(entry) for entry in collections_raw]

    def save(self, collections: list[Collection]) -> bool:
        file_path = self._instance_collections_file()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "collections": [entry.to_dict() for entry in collections]}

        try:
            with open(file_path, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=4, ensure_ascii=True)
            return True
        except Exception as error:
            logger.error(f"Failed to write collections file {file_path}: {error}")
            return False

    def create_collection(
            self,
            name: str,
            description: str = "",
            color: str = DEFAULT_COLLECTION_COLOR,
    ) -> tuple[list[Collection], Collection] | tuple[None, None]:
        cleaned = name.strip()
        if not cleaned:
            return None, None
        collections = self.load()
        new_collection = Collection.create(cleaned, description, color=color)
        collections.append(new_collection)
        if not self.save(collections):
            return None, None
        return collections, new_collection

    def update_collection(self, updated: Collection) -> list[Collection] | None:
        collections = self.load()
        replaced = False
        for index, collection in enumerate(collections):
            if collection.id == updated.id:
                updated.name = updated.name.strip()
                updated.description = updated.description.strip()
                updated.color = _normalize_collection_color(updated.color)
                (
                    updated.cover_type,
                    updated.cover_image_path,
                    updated.cover_package_id,
                ) = _normalize_collection_cover_settings(
                    updated.cover_type,
                    updated.cover_image_path,
                    updated.cover_package_id,
                    updated.package_ids,
                )
                updated.updated_at = _utc_now_iso()
                collections[index] = updated
                replaced = True
                break
        if not replaced:
            return None
        if not self.save(collections):
            return None
        return collections

    def delete_collection(self, collection_id: str) -> list[Collection] | None:
        collections = self.load()
        new_collections = [entry for entry in collections if entry.id != collection_id]
        if len(new_collections) == len(collections):
            return None
        if not self.save(new_collections):
            return None
        return new_collections

    def add_package_ids(
        self, collection_id: str, package_ids: list[str]
    ) -> list[Collection] | None:
        incoming = [_normalize_package_id(pid) for pid in package_ids if pid.strip()]
        if not incoming:
            return None

        collections = self.load()
        for collection in collections:
            if collection.id != collection_id:
                continue
            seen = set(collection.package_ids)
            for package_id in incoming:
                if package_id not in seen:
                    seen.add(package_id)
                    collection.package_ids.append(package_id)
            (
                collection.cover_type,
                collection.cover_image_path,
                collection.cover_package_id,
            ) = _normalize_collection_cover_settings(
                collection.cover_type,
                collection.cover_image_path,
                collection.cover_package_id,
                collection.package_ids,
            )
            collection.updated_at = _utc_now_iso()
            if not self.save(collections):
                return None
            return collections
        return None

    def remove_package_ids(
            self, collection_id: str, package_ids: list[str]
    ) -> list[Collection] | None:
        incoming = {_normalize_package_id(pid) for pid in package_ids if pid.strip()}
        if not incoming:
            return None

        collections = self.load()
        for collection in collections:
            if collection.id != collection_id:
                continue
            collection.package_ids = [
                package_id
                for package_id in collection.package_ids
                if package_id not in incoming
            ]
            (
                collection.cover_type,
                collection.cover_image_path,
                collection.cover_package_id,
            ) = _normalize_collection_cover_settings(
                collection.cover_type,
                collection.cover_image_path,
                collection.cover_package_id,
                collection.package_ids,
            )
            collection.updated_at = _utc_now_iso()
            if not self.save(collections):
                return None
            return collections
        return None

    def set_package_ids(
        self, collection_id: str, package_ids: list[str]
    ) -> list[Collection] | None:
        normalized: list[str] = []
        seen: set[str] = set()
        for package_id in package_ids:
            clean = _normalize_package_id(package_id)
            if clean and clean not in seen:
                seen.add(clean)
                normalized.append(clean)

        collections = self.load()
        for collection in collections:
            if collection.id != collection_id:
                continue
            collection.package_ids = normalized
            (
                collection.cover_type,
                collection.cover_image_path,
                collection.cover_package_id,
            ) = _normalize_collection_cover_settings(
                collection.cover_type,
                collection.cover_image_path,
                collection.cover_package_id,
                collection.package_ids,
            )
            collection.updated_at = _utc_now_iso()
            if not self.save(collections):
                return None
            return collections
        return None
