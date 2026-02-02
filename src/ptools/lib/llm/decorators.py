import os
from functools import wraps

from ptools.utils.decorator_compistor import DecoratorCompositor
from ptools.utils.print import FormatUtils

from .history import HistoryTransformerFactory
from .constants import openai_models, google_models
from .entities import LLMProfile
from .profiles import profiles
from .stores import profiles_store, chats_store

diagnostics = []

def validate_model_key_present(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        model = kwargs.get('model')
        if model in openai_models:
            assert kwargs.get('OPENAI_API_KEY'), "OPENAI_API_KEY is required for OpenAI models."
            os.environ['OPENAI_API_KEY'] = kwargs.get('OPENAI_API_KEY')

            diagnostics.append(FormatUtils.info(f"OpenAI API Key set for model {model}."))

        elif model in google_models:
            assert kwargs.get('GOOGLE_API_KEY'), "GOOGLE_API_KEY is required for Google models."
            os.environ['GOOGLE_API_KEY'] = kwargs.get('GOOGLE_API_KEY')

            diagnostics.append(FormatUtils.info(f"Google API Key set for model {model}."))

        return f(*args, **kwargs)
    return wrapper

def get_profile(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        profile_arg = kwargs.get('profile')
        profile = None
        if profile_arg:
            profile = profiles_store.get_profile_by_name(profile_arg)
            diagnostics.append(FormatUtils.info(f"Using profile: {profile_arg}"))

        if profile is None:
            profile = LLMProfile()
            diagnostics.append(FormatUtils.warning(f"Profile '{profile_arg}' not found. Using default profile."))

        kwargs['profile'] = profile
        kwargs_has_model = 'model' in kwargs and kwargs['model'] is not None
        profile_has_model = profile.model is not None
        if not kwargs_has_model and profile_has_model:
            kwargs['model'] = profile.model
        else:
            kwargs['model'] = 'gemini-2.0-flash'

        diagnostics.append(FormatUtils.info(f"Using model: {kwargs['model']}"))
        diagnostics.append(FormatUtils.info(f"Model was retrieved from profile: {not kwargs_has_model}"))

        return f(*args, **kwargs)

    return wrapper

def get_chat_file(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        history = kwargs.get('history')
        persist = kwargs.get('persist')

        chat_file = None
        if history:
            chat_file = chats_store.get_chat_by_name(history)
            diagnostics.append(FormatUtils.info(f"Using existing chat history: {history}"))
        elif persist:
            chat_file = chats_store.new_chat()
            diagnostics.append(FormatUtils.info(f"Created new persistent chat history: {chat_file}"))
        else:
            chat_file = chats_store.no_persist_chat()
            diagnostics.append(FormatUtils.info(f"Using non-persistent chat history."))

        del kwargs['history']
        del kwargs['persist']

        kwargs['chat'] = chat_file

        return f(*args, **kwargs)
    return wrapper

def get_history_transformer(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        history_transformer_name = kwargs.get('history_transformer')
        history_transformer = HistoryTransformerFactory.get_transformer(history_transformer_name)
        diagnostics.append(FormatUtils.info(f"Using history transformer: {history_transformer_name}"))
        kwargs['history_transformer'] = history_transformer
        return f(*args, **kwargs)
    return wrapper

def get_chat_client(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        model = kwargs.get('model')
        chat_provider = None

        if model in openai_models:
            from ptools.lib.llm.client import OpenAIChatClient
            chat_provider = OpenAIChatClient(model=model)

        elif model in google_models:
            from ptools.lib.llm.client import GoogleChatClient
            chat_provider = GoogleChatClient(model=model)

        kwargs['client'] = chat_provider

        del kwargs['OPENAI_API_KEY']
        del kwargs['GOOGLE_API_KEY']
        del kwargs['model']

        return f(*args, **kwargs)
    return wrapper

def ensure_default_profiles_are_initialized(f):
    for name, profile in profiles.items():
        if profiles_store.get(name) is None:
            profiles_store.add(name, profile)
    return f

def print_diagnostics(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        list(map(lambda x: print(x), diagnostics)) if kwargs.get('debug', False) else None
        del kwargs['debug']
        return f(*args, **kwargs)
    return wrapper

before_call = DecoratorCompositor.from_list([
    get_profile,
    validate_model_key_present,
    get_chat_file,
    get_history_transformer,
    get_chat_client,
    ensure_default_profiles_are_initialized,
    print_diagnostics
])