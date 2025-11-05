import click


from ptools.utils.print import FormatUtils
from ptools.utils.config import ConfigFile
import ptools.utils.require as require

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import  Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import RadioList, Box
from prompt_toolkit.shortcuts import clear

config = ConfigFile('literals', quiet=True)

class RadioListWithCallback(RadioList):
    def __init__(self, values, on_selection_change=None):
        super().__init__(values)
        self.on_selection_change = on_selection_change

    def _handle_enter(self):
        super()._handle_enter()
        if self.on_selection_change:
            self.on_selection_change(self.current_value)

class LiteralsApp():
    def __init__(self, items, selected_text="Selected literal: {}"):
        self.items = items
        self.radio_list = RadioListWithCallback(items, on_selection_change=self.on_select)
        self.layout = Layout(
            Box(
                self.radio_list,
                padding=0
            ),
            focused_element=self.radio_list
        )
        self.kb = KeyBindings()
        self.kb.add("escape")(self.on_cancel)
        self.app = Application(layout=self.layout, key_bindings=self.kb)
        self.selected = []
        self.selected_text = selected_text

    def on_select(self, value):
        self.selected = value
        self.exit()

    def on_cancel(self, event):
        event.app.exit()
        self.exit()

    def run(self):
        self.app.run()
        return self.selected

    def exit(self):
        self.app.layout = Layout(
            Window(
                content=FormattedTextControl(
                    text=self.selected_text.format(self.selected)
                )
            )
        )
        self.app.invalidate()
        self.app.exit()


@click.command(name="lget")
@require.library("pyperclip", prompt_install=True)
@click.argument('collection', required=False)
@click.option('--choose-collection', '-c', is_flag=True, default=False, help='Choose collection interactively.')
def cli(collection, choose_collection):
    """Interactively select literals from the configured library."""
    import pyperclip

    all_collections = config.data

    if choose_collection and not collection:
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
    elif choose_collection and collection:
        click.echo(FormatUtils.error("Cannot use --choose-collection with a specified collection."))
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

    app = LiteralsApp(items, selected_text="[Success] Literal copied to clipboard: {}")
    selected = app.run()

    if selected:
        literal_value = selected
        pyperclip.copy(literal_value)
