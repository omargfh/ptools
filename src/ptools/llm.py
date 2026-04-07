"""LLM chat interface.

Implements the :command:`ptools llm` CLI — a lightweight wrapper around
OpenAI and Google chat models — and :command:`ptools llm-opts`, a group
of administrative subcommands for managing API keys, profiles, and
persisted chat histories.

One-shot prompts, interactive chat sessions, history transformers, and
per-profile model overrides are all handled in :func:`cli`. The heavier
model client, session, and store logic lives under
:mod:`ptools.lib.llm`.
"""

# version: 1.0.4
import click
import os

import ptools.utils.require as require
from ptools.utils.print import FormatUtils

from ptools.lib.llm.constants import model_choices
from ptools.lib.llm.history import HistoryTransformerFactory


def _get_key_store():
    from ptools.lib.llm.stores import key_store
    return key_store


def _initialize_default_profiles(profiles_store):
    from ptools.lib.llm.profiles import profiles
    for name, profile in profiles.items():
        if profiles_store.get(name) is None:
            profiles_store.add(name, profile)


def _resolve_profile(profiles_store, profile_name: str | None):
    from ptools.lib.llm.entities import LLMProfile
    profile = profiles_store.get_profile_by_name(profile_name) if profile_name else None
    if profile is None:
        return LLMProfile(), [
            FormatUtils.warning(f"Profile '{profile_name}' not found. Using default profile.")
        ]

    return profile, [FormatUtils.info(f"Using profile: {profile_name}")]


def _resolve_chat(chats_store, history: str | None, persist: bool):
    diagnostics = []
    if history:
        diagnostics.append(FormatUtils.info(f"Using existing chat history: {history}"))
        return chats_store.get_chat_by_name(history), diagnostics
    if persist:
        chat_file = chats_store.new_chat()
        diagnostics.append(FormatUtils.info(f"Created new persistent chat history: {chat_file}"))
        return chat_file, diagnostics

    diagnostics.append(FormatUtils.info("Using non-persistent chat history."))
    return chats_store.no_persist_chat(), diagnostics


def _resolve_client(model: str):
    from ptools.lib.llm.client import GoogleChatClient, OpenAIChatClient
    from ptools.lib.llm.constants import google_models, openai_models

    if model in openai_models:
        return OpenAIChatClient(model=model)
    if model in google_models:
        return GoogleChatClient(model=model)
    raise click.ClickException(f"Model '{model}' is not supported.")

@click.command()
@require.library('openai', prompt_install=True)
@require.library('prompt_toolkit', prompt_install=True)
@require.library('pygments', prompt_install=True)
@click.argument('message', required=False, nargs=-1)
@click.option('--model', '-m', type=click.Choice(model_choices), help='Language model to use.')
@click.option(
    '--history-transformer', '-t',
    default='pass_through',
    type=click.Choice(HistoryTransformerFactory.list_transformers()),
    help='History transformer to use.'
)
@click.option('--history', '-h', help='Name of the history file to use.')
@click.option('--profile', '-p',  help='Name of the profile to use.', default='default')
@click.option('--interactive/--no-interactive', '-i/-I', default=False, help='Use chat interface.')
@click.option('--persist/--no-persist', '-s/-S', default=False, help='Persist chat file to disk when creating a new chat session without --chat-file.')
@click.option('--debug/--no-debug', '-d/-D', default=False, help='Enable debug mode to print diagnostic information.')
def cli(
    message: str | None,
    model: str | None,
    history_transformer: str,
    history: str | None,
    profile: str | None,
    interactive: bool,
    persist: bool,
    debug: bool,
):
    """Interact with a chat interface."""
    from ptools.lib.llm.constants import google_models, openai_models
    from ptools.lib.llm.prompt import parse_prompt
    from ptools.lib.llm.session import ChatSession
    from ptools.lib.llm.stores import chats_store, profiles_store
    from ptools.lib.llm.commands import commands
    from ptools.lib.llm.repl import start_chat

    key_store = _get_key_store()
    _initialize_default_profiles(profiles_store)

    diagnostics = []
    profile_obj, profile_diagnostics = _resolve_profile(profiles_store, profile)
    diagnostics.extend(profile_diagnostics)

    if model is None:
        model = profile_obj.model if profile_obj.model is not None else 'gemini-2.0-flash'
    diagnostics.append(FormatUtils.info(f"Using model: {model}"))
    diagnostics.append(FormatUtils.info(f"Model was retrieved from profile: {profile_obj.model is not None and profile_obj.model == model}"))

    openai_api_key = os.environ.get('OPENAI_API_KEY') or key_store.get('OPENAI_API_KEY')
    google_api_key = os.environ.get('GOOGLE_API_KEY') or key_store.get('GOOGLE_API_KEY')

    if model in openai_models:
        if not openai_api_key:
            raise click.ClickException("OPENAI_API_KEY is required for OpenAI models.")
        os.environ['OPENAI_API_KEY'] = openai_api_key
        diagnostics.append(FormatUtils.info(f"OpenAI API Key set for model {model}."))
    elif model in google_models:
        if not google_api_key:
            raise click.ClickException("GOOGLE_API_KEY is required for Google models.")
        os.environ['GOOGLE_API_KEY'] = google_api_key
        diagnostics.append(FormatUtils.info(f"Google API Key set for model {model}."))

    chat, chat_diagnostics = _resolve_chat(chats_store, history, persist)
    diagnostics.extend(chat_diagnostics)

    history_transformer_obj = HistoryTransformerFactory.get_transformer(history_transformer)
    diagnostics.append(FormatUtils.info(f"Using history transformer: {history_transformer}"))

    client = _resolve_client(model)

    if debug:
        for diagnostic in diagnostics:
            print(diagnostic)

    session = ChatSession(
        provider=client,
        history_transformer=history_transformer_obj,
        chat_file=chat,
        profile=profile_obj
    )

    context = {
        'history': lambda: session.chat_file.messages,
        'profile': lambda: session.profile,
        'commands': commands
    }

    if message:
        message = parse_prompt(' '.join(message), context=context)
        response = session.send_message(message)
        for chunk in response:
            print(chunk, end='', flush=True)
    elif interactive:
        start_chat(
            commands,
            exit_commands=("/exit", "/quit", '/q'),
            on_user_message=lambda msg: session.send_message(msg),
            history=session.chat_file.messages,
            context=context
        )
    else:
        click.echo(FormatUtils.error("No message provided. Use --chat for interactive mode."))


@click.group()
def opts():
    """AI related commands."""
    pass

@opts.command(name='set-api-key')
@click.option('--service', '-s', type=click.Choice(['openai', 'serperdev', 'google']), required=True, help='Service to set the API key for.')
@click.argument('key', required=False)
def set_api_key(service: str, key: str | None):
    """Set the API key for a specific service."""
    key_store = _get_key_store()
    if not key:
        key = click.prompt(f'Enter API key for {service}', hide_input=True)

    key_name = f'{service.upper()}_API_KEY'
    key_store.set(key_name, key)
    click.echo(FormatUtils.success(f'Set API key for {service} in config file.'))

@opts.command(name='list-api-keys')
def list_api_keys():
    """List all stored API keys."""
    from ptools.lib.llm.stores import key_store
    keys = key_store.list()
    if not keys:
        click.echo(FormatUtils.info('No API keys found.'))
        return
    for name, value in keys.items():
        display_value = "*" * len(value) if value else "(not set)"
        click.echo(FormatUtils.bold(f'{name}: '), nl=False)
        click.echo(FormatUtils.highlight(display_value, 'yellow'))

@opts.command(name='add-profile')
@click.argument('name', required=True)
@click.argument('file', type=click.Path(exists=True), required=True)
@click.option('--copy', '-c', is_flag=True, help='Copy the file to the config directory instead of linking it.')
def add_profile(name: str, file: str, copy: bool):
    """Add a new LLM profile."""
    from ptools.lib.llm.stores import profiles_store
    if copy:
        import shutil
        dest_path = profiles_store.get_profile_path_from_name(os.path.basename(file).rsplit('.', 1)[0])
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy(file, dest_path)
        file = dest_path
    else:
        file = os.path.abspath(file)
    profiles_store.set(name, file)
    click.echo(FormatUtils.success(f'Added profile "{name}" with file "{file}" to config.'))

@opts.command(name='create-profile')
def create_profile():
    """Create a new LLM profile interactively."""
    from ptools.lib.llm.entities import LLMProfile
    from ptools.lib.llm.stores import profiles_store
    name = click.prompt('Enter profile name')
    if profiles_store.get(name):
        click.echo(FormatUtils.error(f'Profile with name "{name}" already exists.'))
        return

    temperature = click.prompt('Enter temperature', type=float, default=0.7)
    max_tokens = click.prompt('Enter max tokens', type=int, default=1024)
    presence_penalty = click.prompt('Enter presence penalty', type=float, default=0.0)
    frequency_penalty = click.prompt('Enter frequency penalty', type=float, default=0.0)
    system_prompt = click.prompt('Enter system prompt', type=str, default="You are a helpful assistant.", )

    profile = LLMProfile(
        temperature=temperature,
        max_tokens=max_tokens,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        system_prompt=system_prompt
    )

    profiles_store.add(name, profile)
    click.echo(FormatUtils.success(f'Created profile "{name}".'))

@opts.command(name='list-profiles')
def list_profiles():
    """List all LLM profiles."""
    from ptools.lib.llm.stores import profiles_store
    profiles = profiles_store.list()
    if not profiles:
        click.echo(FormatUtils.info('No profiles found.'))
        return
    for name, path in profiles.items():
        click.echo(FormatUtils.info(f'{name}: {path}'))

@opts.command(name='delete-profile')
@click.confirmation_option(prompt='Are you sure you want to delete this profile?')
@click.argument('name', required=True)
def delete_profile(name: str):
    """Delete an LLM profile."""
    from ptools.lib.llm.stores import profiles_store
    if profiles_store.get(name) is None:
        click.echo(FormatUtils.error(f'Profile "{name}" does not exist.'))
        return
    profiles_store.delete(name)
    click.echo(FormatUtils.success(f'Deleted profile "{name}".'))

@opts.command(name='prune-chats')
@click.confirmation_option(prompt='Are you sure you want to prune all chat files? This action cannot be undone.')
def prune_chats():
    """Delete all chat files."""
    from ptools.lib.llm.stores import chats_store
    chat_files = chats_store.list()
    if not chat_files:
        click.echo(FormatUtils.info('No chat files to prune.'))
        return
    for name in list(chat_files.keys()):
        chats_store.delete_chat(name)
        click.echo(FormatUtils.success(f'Deleted chat file "{name}".'))
    click.echo(FormatUtils.success('Pruned all chat files.'))

@opts.command(name='list-chats')
def list_chats():
    """List all chat files."""
    from ptools.lib.llm.stores import chats_store
    chat_files = chats_store.list()

    if not chat_files:
        click.echo(FormatUtils.info('No chat files found.'))
        return

    for name, path in chat_files.items():
        import datetime
        last_modified = os.path.getmtime(path)
        last_modified = datetime.datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')

        click.echo(FormatUtils.bold(f'  - {name}: '), nl=False)
        click.echo(FormatUtils.highlight(f'{path})', 'yellow'), nl=False)
        click.echo(f" (Last modified: {last_modified})")
