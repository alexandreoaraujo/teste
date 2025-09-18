from decimal import Decimal
from pathlib import Path

import pytest

from shopping_app import DataStore, EntryNotFoundError, ItemNotFoundError


def create_store(tmp_path: Path) -> DataStore:
    storage = tmp_path / "data.json"
    return DataStore(storage)


def test_add_and_best_prices(tmp_path):
    store = create_store(tmp_path)
    store.add_price("Alho", Decimal("5"), is_promo=False, store="Mercado A", unit="kg")
    store.add_price("Alho", Decimal("4.5"), is_promo=False, store="Mercado B", unit="kg")
    store.add_price("Alho", Decimal("3.5"), is_promo=True, store="Mercado C", unit="kg")

    item = store.get_item("alho")
    normal = item.best_price(is_promo=False)
    promo = item.best_price(is_promo=True)

    assert normal is not None
    assert promo is not None
    assert normal.price == Decimal("4.50")
    assert normal.store == "Mercado B"
    assert promo.price == Decimal("3.50")
    assert promo.is_promo is True

    # garante que a persistência funciona
    new_store = DataStore(store.storage_path)
    new_item = new_store.get_item("Alho")
    assert len(new_item.entries) == 3


def test_update_entry_changes_fields(tmp_path):
    store = create_store(tmp_path)
    store.add_price("Tomate", Decimal("7"), is_promo=False)
    store.update_entry(
        "tomate",
        1,
        price=Decimal("6.8"),
        is_promo=True,
        store="Quitanda",
        unit="kg",
        notes="Orgânico",
    )

    item = store.get_item("TOMATE")
    entry = item.find_entry(1)
    assert entry is not None
    assert entry.price == Decimal("6.80")
    assert entry.is_promo is True
    assert entry.store == "Quitanda"
    assert entry.unit == "kg"
    assert entry.notes == "Orgânico"
    assert entry.timestamp  # campo preenchido


def test_remove_entry(tmp_path):
    store = create_store(tmp_path)
    store.add_price("Café", Decimal("15"), is_promo=False)
    store.add_price("Café", Decimal("12"), is_promo=True)
    store.remove_entry("café", 1)

    item = store.get_item("Café")
    assert len(item.entries) == 1
    assert item.entries[0].id == 2

    with pytest.raises(EntryNotFoundError):
        store.remove_entry("Café", 3)



def test_search_and_rename(tmp_path):
    store = create_store(tmp_path)
    store.add_price("Batata Doce", Decimal("4.2"), is_promo=False)
    store.add_price("Batata Inglesa", Decimal("3.0"), is_promo=False)

    results = store.search_items("batata")
    assert [item.name for item in results] == ["Batata Doce", "Batata Inglesa"]

    store.rename_item("Batata Inglesa", "Batata Branca")
    assert [item.name for item in store.list_items()] == ["Batata Branca", "Batata Doce"]

    with pytest.raises(ItemNotFoundError):
        store.get_item("Batata Inglesa")
