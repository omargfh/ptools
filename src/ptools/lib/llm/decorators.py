import os
from functools import wraps
from typing import List, Dict, Callable

from ptools.utils.decorator_compistor import DecoratorCompositor

from .client import OpenAIChatClient, GoogleChatClient
from .constants import openai_models, google_models
from .profiles import profiles
from .stores import profiles_store

def validate_model_key_present(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        model = kwargs.get('model')
        if model in openai_models:
            assert kwargs.get('OPENAI_API_KEY'), "OPENAI_API_KEY is required for OpenAI models."
            os.environ['OPENAI_API_KEY'] = kwargs.get('OPENAI_API_KEY')
        elif model in google_models:
            assert kwargs.get('GOOGLE_API_KEY'), "GOOGLE_API_KEY is required for Google models."
            os.environ['GOOGLE_API_KEY'] = kwargs.get('GOOGLE_API_KEY')
            
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

before_call = DecoratorCompositor.from_list([
    validate_model_key_present,
    get_chat_client,
    ensure_default_profiles_are_initialized,
])