import click


from ptools.utils.print import FormatUtils
from ptools.utils.config import ConfigFile
import ptools.utils.require as require

from ptools.lib.tui.select import SelectApp, select, text

config = ConfigFile('literals', quiet=True)

# Sentinel option in the collection picker for "create a new collection
# instead of choosing an existing one".
NEW_COLLECTION = "+ new collection"

class LiteralsApp(SelectApp):
    """Select picker with the literals default selection message."""

    def __init__(self, items, selected_text="Selected literal: {}", **kwargs):
        super().__init__(items, selected_text=selected_text, **kwargs)


@click.command(name="lget")
@require.library("pyperclip", prompt_install=True)
@click.argument('collection', required=False)
@click.option('--choose-collection', '-c', is_flag=True, default=False, help='Choose collection interactively.')
@click.option('--stay-alive', '-s', is_flag=True, default=False, help='Keep the application running after selection to select more literals.')
def cli(collection, choose_collection, stay_alive):
    """Interactively select literals from the configured library.

    \b
    Example:
      $ ptools lget snippets
      # Opens an interactive selector and copies the selected literal to the clipboard.

    \b
      $ ptools lget missing-collection
      WARNING No literals found in the specified collection.
    """
    import pyperclip

    all_collections = config.data

    if choose_collection and not collection and not stay_alive:
        collections = list({
            # e.g. "my_collection (5) -> my_collection"
            (k, f"{k} ({len(v.values())})")
            for k, v in all_collections.items()
        })
        app = LiteralsApp(collections, selected_text="=== {} ===")
        selected = app.run()
        if selected:
            collection = selected
        else:
            click.echo(FormatUtils.warning("No collection selected."))
            return
    elif choose_collection and collection or choose_collection and stay_alive:
        click.echo(FormatUtils.error("Cannot use --choose-collection with a specified collection or --stay-alive/-s."))
        return

    items = [
        (item_value, item_value)
        for col_name, col_items_dict in all_collections.items()
        for _, item_value in col_items_dict.items()
        if col_name == collection or not collection
    ]

    if not items:
        click.echo(FormatUtils.warning("No literals found in the specified collection."))
        return

    def select_handler(value):
        pyperclip.copy(value)

    args = [items]
    kwargs = {
        "selected_text": "[Success] Literal copied to clipboard: {}",
        "select_handler": select_handler
    }

    selected = None
    if stay_alive:
        while True:
            app = LiteralsApp(*args, **kwargs, selected=selected)
            selected = app.run()
            if not selected:
                break
    else:
        LiteralsApp(*args, **kwargs).run()


@click.command(name="lget-add")
def add():
    """Interactively add a new literal to a collection.

    Pick an existing collection with the arrow keys, or choose the
    "+ new collection" option to name a new one, then enter a key and a
    value for the new entry. The entry is rejected if the key already
    exists in the target collection, and otherwise persisted immediately
    so it's visible to ``ptools lget`` on the next invocation.

    \b
    Example:
      $ ptools lget-add
      ? Select a collection:
      ❯ cli_emojis (14)
        filesystem_emojis (10)
        + new collection
      ? Key: tada
      ? Value: 🎉
      [Success] Added 'tada' to 'cli_emojis'.
    """
    all_collections = config.data

    options = [
        (name, f"{name} ({len(values)})")
        for name, values in all_collections.items()
    ]
    options.append((NEW_COLLECTION, NEW_COLLECTION))

    collection = select(
        options, "Select a collection:", app_cls=LiteralsApp, selected_text="Selected: {}"
    )
    if not collection:
        click.echo(FormatUtils.warning("No collection selected."))
        return

    if collection == NEW_COLLECTION:
        collection = text("New collection name:", placeholder="e.g. snippets").strip()
        if not collection:
            click.echo(FormatUtils.warning("No collection name given."))
            return

    existing = all_collections.get(collection, {})

    key = text("Key:", placeholder="e.g. success").strip()
    if not key:
        click.echo(FormatUtils.warning("No key given."))
        return

    if key in existing:
        click.echo(FormatUtils.error(f"Key '{key}' already exists in collection '{collection}'."))
        return

    value = text("Value:", placeholder="e.g. ✅").strip()
    if not value:
        click.echo(FormatUtils.warning("No value given."))
        return

    config.set(collection, {**existing, key: value})
    click.echo(FormatUtils.success(f"Added '{key}' to '{collection}'."))
