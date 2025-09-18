"""Camada de dados para o gerenciador de preços."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
from typing import Dict, List, Optional

CURRENCY_QUANTIZE = Decimal("0.01")


class DataStoreError(Exception):
    """Erro genérico lançado pelo :class:`DataStore`."""


class ItemNotFoundError(DataStoreError):
    """Exceção lançada quando um item não existe na base de dados."""


class EntryNotFoundError(DataStoreError):
    """Exceção lançada quando um preço específico não existe."""


@dataclass
class PriceEntry:
    """Representa uma observação de preço para um item."""

    id: int
    price: Decimal
    is_promo: bool
    store: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )

    def to_dict(self) -> Dict[str, object]:
        """Converte a entrada em um dicionário serializável."""
        return {
            "id": self.id,
            "price": format_decimal(self.price),
            "is_promo": self.is_promo,
            "store": self.store,
            "unit": self.unit,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PriceEntry":
        """Cria uma entrada a partir de um dicionário."""
        return cls(
            id=int(data["id"]),
            price=parse_decimal(str(data["price"])),
            is_promo=bool(data["is_promo"]),
            store=clean_text(data.get("store")),
            unit=clean_text(data.get("unit")),
            notes=clean_text(data.get("notes")),
            timestamp=str(data.get("timestamp") or ""),
        )

    def update(
        self,
        *,
        price: Optional[Decimal] = None,
        is_promo: Optional[bool] = None,
        store: Optional[str] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Atualiza os campos da entrada."""
        if price is not None:
            self.price = quantize_price(price)
        if is_promo is not None:
            self.is_promo = is_promo
        if store is not None:
            self.store = clean_text(store)
        if unit is not None:
            self.unit = clean_text(unit)
        if notes is not None:
            self.notes = clean_text(notes)
        self.timestamp = datetime.utcnow().isoformat(timespec="seconds")


@dataclass
class Item:
    """Representa um item cadastrado na base de dados."""

    name: str
    entries: List[PriceEntry] = field(default_factory=list)
    next_entry_id: int = 1

    def add_entry(
        self,
        price: Decimal,
        *,
        is_promo: bool,
        store: Optional[str] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PriceEntry:
        entry = PriceEntry(
            id=self.next_entry_id,
            price=quantize_price(price),
            is_promo=is_promo,
            store=clean_text(store),
            unit=clean_text(unit),
            notes=clean_text(notes),
        )
        self.entries.append(entry)
        self.next_entry_id += 1
        return entry

    def find_entry(self, entry_id: int) -> Optional[PriceEntry]:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def remove_entry(self, entry_id: int) -> None:
        entry = self.find_entry(entry_id)
        if entry is None:
            raise EntryNotFoundError(f"Não existe preço com id {entry_id}")
        self.entries.remove(entry)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "next_entry_id": self.next_entry_id,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Item":
        entries_data = data.get("entries", [])
        entries = [PriceEntry.from_dict(entry) for entry in entries_data]
        next_entry_id = int(data.get("next_entry_id") or (len(entries) + 1))
        return cls(name=str(data.get("name", "")), entries=entries, next_entry_id=next_entry_id)

    def best_price(self, *, is_promo: bool) -> Optional[PriceEntry]:
        candidates = [entry for entry in self.entries if entry.is_promo is is_promo]
        if not candidates:
            return None
        return min(candidates, key=lambda entry: entry.price)


class DataStore:
    """Persistência de itens e preços em um arquivo JSON."""

    def __init__(self, storage_path: Path | str = "shopping_data.json") -> None:
        self.storage_path = Path(storage_path)
        self._items: Dict[str, Item] = {}
        self.load()

    # ------------------------------------------------------------------
    # Operações públicas
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Carrega os dados do arquivo configurado."""
        if not self.storage_path.exists():
            self._items = {}
            return
        with self.storage_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        items: Dict[str, Item] = {}
        for key, item_data in raw.get("items", {}).items():
            items[key] = Item.from_dict(item_data)
        self._items = items

    def save(self) -> None:
        """Persiste os dados para o arquivo configurado."""
        if not self.storage_path.parent.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: item.to_dict() for key, item in self._items.items()}
        payload = {"items": data}
        with self.storage_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

    def list_items(self) -> List[Item]:
        """Retorna todos os itens ordenados alfabeticamente."""
        return sorted(self._items.values(), key=lambda item: item.name.lower())

    def search_items(self, query: str) -> List[Item]:
        """Pesquisa itens cujo nome contenha a consulta (case insensitive)."""
        normalized_query = query.strip().lower()
        results = [
            item
            for key, item in self._items.items()
            if normalized_query in key or normalized_query in item.name.lower()
        ]
        return sorted(results, key=lambda item: item.name.lower())

    def get_item(self, name: str) -> Item:
        key = self._normalize_name(name)
        try:
            return self._items[key]
        except KeyError as exc:
            raise ItemNotFoundError(f"{name}") from exc

    def add_price(
        self,
        name: str,
        price: Decimal,
        *,
        is_promo: bool,
        store: Optional[str] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PriceEntry:
        key = self._normalize_name(name)
        item = self._items.get(key)
        if item is None:
            item = Item(name=name.strip(), entries=[], next_entry_id=1)
            self._items[key] = item
        entry = item.add_entry(
            price,
            is_promo=is_promo,
            store=store,
            unit=unit,
            notes=notes,
        )
        self.save()
        return entry

    def update_entry(
        self,
        name: str,
        entry_id: int,
        *,
        price: Optional[Decimal] = None,
        is_promo: Optional[bool] = None,
        store: Optional[str] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PriceEntry:
        item = self.get_item(name)
        entry = item.find_entry(entry_id)
        if entry is None:
            raise EntryNotFoundError(f"{entry_id}")
        entry.update(
            price=price,
            is_promo=is_promo,
            store=store,
            unit=unit,
            notes=notes,
        )
        self.save()
        return entry

    def remove_entry(self, name: str, entry_id: int) -> None:
        item = self.get_item(name)
        item.remove_entry(entry_id)
        self.save()

    def rename_item(self, old_name: str, new_name: str) -> Item:
        old_key = self._normalize_name(old_name)
        try:
            item = self._items[old_key]
        except KeyError as exc:
            raise ItemNotFoundError(f"{old_name}") from exc
        new_key = self._normalize_name(new_name)
        if new_key != old_key and new_key in self._items:
            raise DataStoreError("Já existe um item com esse nome")
        del self._items[old_key]
        item.name = new_name.strip()
        self._items[new_key] = item
        self.save()
        return item

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _normalize_name(self, name: str) -> str:
        return name.strip().lower()


# ----------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------

def parse_decimal(value: str) -> Decimal:
    """Converte uma string em :class:`Decimal` usando duas casas."""
    normalized = value.strip().replace("R$", "").replace(" ", "").replace(",", ".")
    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Valor inválido para preço: {value}") from exc
    return quantize_price(decimal_value)


def quantize_price(price: Decimal) -> Decimal:
    return price.quantize(CURRENCY_QUANTIZE, rounding=ROUND_HALF_UP)


def format_decimal(price: Decimal) -> str:
    """Formata um decimal como string com duas casas decimais."""
    return f"{quantize_price(price):.2f}"


def clean_text(value: Optional[str]) -> Optional[str]:
    """Remove espaços em branco e converte strings vazias para ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


__all__ = [
    "DataStore",
    "Item",
    "PriceEntry",
    "DataStoreError",
    "ItemNotFoundError",
    "EntryNotFoundError",
    "parse_decimal",
    "format_decimal",
    "quantize_price",
    "clean_text",
]
