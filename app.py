"""Aplicativo de linha de comando para gerenciar preços de compras."""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from typing import Iterable

from shopping_app import (
    DataStore,
    EntryNotFoundError,
    Item,
    ItemNotFoundError,
    PriceEntry,
    parse_decimal,
)


def parse_price(value: str) -> Decimal:
    """Função auxiliar para o argparse aceitar valores monetários."""
    try:
        return parse_decimal(value)
    except ValueError as exc:  # pragma: no cover - transformação em erro do argparse
        raise argparse.ArgumentTypeError(str(exc)) from exc


def configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Registre e consulte os menores preços encontrados para cada item.",
    )
    parser.add_argument(
        "--storage",
        default="shopping_data.json",
        help="Caminho do arquivo onde os dados serão salvos (padrão: shopping_data.json)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ------------------------------------------------------------------
    # add
    # ------------------------------------------------------------------
    add_parser = subparsers.add_parser("add", help="Adiciona um preço para um item")
    add_parser.add_argument("name", help="Nome do item")
    add_parser.add_argument("price", type=parse_price, help="Preço encontrado")
    add_parser.add_argument(
        "--promo",
        action="store_true",
        help="Informe caso o valor seja de uma promoção",
    )
    add_parser.add_argument("--store", help="Onde o preço foi encontrado")
    add_parser.add_argument("--unit", help="Unidade de medida (ex.: kg, litro)")
    add_parser.add_argument("--notes", help="Observações adicionais")
    add_parser.set_defaults(func=cmd_add)

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------
    list_parser = subparsers.add_parser("list", help="Lista todos os itens cadastrados")
    list_parser.add_argument(
        "--details",
        action="store_true",
        help="Exibe também todas as observações de preço registradas",
    )
    list_parser.set_defaults(func=cmd_list)

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------
    search_parser = subparsers.add_parser("search", help="Pesquisa itens pelo nome")
    search_parser.add_argument("query", help="Texto para pesquisar")
    search_parser.set_defaults(func=cmd_search)

    # ------------------------------------------------------------------
    # entries
    # ------------------------------------------------------------------
    entries_parser = subparsers.add_parser(
        "entries", help="Mostra todos os preços cadastrados para um item"
    )
    entries_parser.add_argument("name", help="Nome do item")
    entries_parser.set_defaults(func=cmd_entries)

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    update_parser = subparsers.add_parser(
        "update", help="Atualiza um preço específico de um item",
    )
    update_parser.add_argument("name", help="Nome do item")
    update_parser.add_argument("entry_id", type=int, help="Identificador do preço")
    update_parser.add_argument(
        "--price",
        type=parse_price,
        help="Novo valor",
    )
    promo_group = update_parser.add_mutually_exclusive_group()
    promo_group.add_argument(
        "--promo",
        action="store_true",
        help="Marca a entrada como preço de promoção",
    )
    promo_group.add_argument(
        "--normal",
        action="store_true",
        help="Marca a entrada como preço normal",
    )
    update_parser.add_argument("--store", help="Atualiza o nome da loja")
    update_parser.add_argument("--unit", help="Atualiza a unidade de medida")
    update_parser.add_argument("--notes", help="Atualiza as observações")
    update_parser.set_defaults(func=cmd_update)

    # ------------------------------------------------------------------
    # remove
    # ------------------------------------------------------------------
    remove_parser = subparsers.add_parser(
        "remove", help="Remove uma observação de preço",)
    remove_parser.add_argument("name", help="Nome do item")
    remove_parser.add_argument("entry_id", type=int, help="Identificador do preço")
    remove_parser.set_defaults(func=cmd_remove)

    # ------------------------------------------------------------------
    # rename
    # ------------------------------------------------------------------
    rename_parser = subparsers.add_parser("rename", help="Renomeia um item")
    rename_parser.add_argument("old_name", help="Nome atual do item")
    rename_parser.add_argument("new_name", help="Novo nome do item")
    rename_parser.set_defaults(func=cmd_rename)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = configure_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    store = DataStore(args.storage)

    try:
        return args.func(args, store)
    except ItemNotFoundError as exc:
        print(f"Item não encontrado: {exc}", file=sys.stderr)
        return 1
    except EntryNotFoundError as exc:
        print(f"Registro de preço não encontrado: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - tratamento genérico
        print(f"Erro inesperado: {exc}", file=sys.stderr)
        return 1


# ----------------------------------------------------------------------
# Comandos
# ----------------------------------------------------------------------

def cmd_add(args: argparse.Namespace, store: DataStore) -> int:
    entry = store.add_price(
        args.name,
        args.price,
        is_promo=args.promo,
        store=args.store,
        unit=args.unit,
        notes=args.notes,
    )
    item = store.get_item(args.name)
    print(
        "Preço cadastrado!",
        f"Item: {item.name}",
        f"Identificador do preço: {entry.id}",
        sep="\n",
    )
    return 0


def cmd_list(args: argparse.Namespace, store: DataStore) -> int:
    items = store.list_items()
    if not items:
        print("Nenhum item cadastrado ainda. Utilize o comando 'add' para começar.")
        return 0

    print("Itens cadastrados:")
    for index, item in enumerate(items):
        print_item_summary(item)
        if args.details:
            print_entries(item.entries, header="  Preços registrados:")
        if index < len(items) - 1:
            print()
    return 0


def cmd_search(args: argparse.Namespace, store: DataStore) -> int:
    results = store.search_items(args.query)
    if not results:
        print("Nenhum item encontrado para a pesquisa informada.")
        return 0

    for index, item in enumerate(results):
        print_item_summary(item)
        if index < len(results) - 1:
            print()
    return 0


def cmd_entries(args: argparse.Namespace, store: DataStore) -> int:
    item = store.get_item(args.name)
    if not item.entries:
        print("Ainda não há preços cadastrados para este item.")
        return 0
    print(f"Preços cadastrados para {item.name}:")
    print_entries(item.entries)
    return 0


def cmd_update(args: argparse.Namespace, store: DataStore) -> int:
    is_promo = None
    if args.promo:
        is_promo = True
    elif args.normal:
        is_promo = False

    entry = store.update_entry(
        args.name,
        args.entry_id,
        price=args.price,
        is_promo=is_promo,
        store=args.store,
        unit=args.unit,
        notes=args.notes,
    )
    print("Preço atualizado com sucesso!")
    print(describe_entry(entry, indent="  "))
    return 0


def cmd_remove(args: argparse.Namespace, store: DataStore) -> int:
    store.remove_entry(args.name, args.entry_id)
    print("Registro removido com sucesso.")
    return 0


def cmd_rename(args: argparse.Namespace, store: DataStore) -> int:
    item = store.rename_item(args.old_name, args.new_name)
    print(f"Item renomeado para {item.name}.")
    return 0


# ----------------------------------------------------------------------
# Utilidades para exibição
# ----------------------------------------------------------------------

def print_item_summary(item: Item) -> None:
    print(f"- {item.name}")
    normal = item.best_price(is_promo=False)
    promo = item.best_price(is_promo=True)
    if normal:
        print(
            "    Melhor preço normal: "
            f"{describe_entry(normal, show_price_type=False, show_timestamp=False)}"
        )
    else:
        print("    Sem preços normais cadastrados.")
    if promo:
        print(
            "    Melhor preço em promoção: "
            f"{describe_entry(promo, show_price_type=False, show_timestamp=False)}"
        )
    else:
        print("    Sem preços em promoção cadastrados.")


def print_entries(entries: Iterable[PriceEntry], header: str | None = None) -> None:
    if header:
        print(header)
    for entry in sorted(entries, key=lambda e: (e.price, e.id)):
        print(describe_entry(entry, include_id=True, indent="    "))


def describe_entry(
    entry: PriceEntry,
    *,
    include_id: bool = False,
    indent: str = "",
    show_price_type: bool = True,
    show_timestamp: bool = True,
) -> str:
    parts = [format_currency(entry.price)]
    if entry.unit:
        parts.append(f"por {entry.unit}")
    text = " ".join(parts)

    details = []
    if include_id:
        details.append(f"id {entry.id}")
    if show_price_type:
        details.append("promoção" if entry.is_promo else "preço normal")
    if entry.store:
        details.append(f"loja: {entry.store}")
    if entry.notes:
        details.append(entry.notes)
    if show_timestamp:
        details.append(f"atualizado em {entry.timestamp}")

    detail_text = "; ".join(details)
    return f"{indent}{text} ({detail_text})"


def format_currency(value: Decimal) -> str:
    formatted = f"{value:.2f}".replace(".", ",")
    return f"R$ {formatted}"


if __name__ == "__main__":  # pragma: no cover - permite usar como script
    sys.exit(main())
