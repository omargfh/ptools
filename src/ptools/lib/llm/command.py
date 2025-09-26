from __future__ import annotations
from typing import List, Callable, Any
from pydantic import BaseModel, model_validator, SkipValidation

class CommandArgument(BaseModel):
    name: str | None = None
    value: SkipValidation[Any] = None
    required: bool = False
    kind: str = 'posarg'
    parser: Callable[[Any], Any] = lambda x: x
    parser_name: str | None = None

    model_config = {
        'arbitrary_types_allowed': True
    }
    
    def __repr__(self):
        name = self.name if self.name else "arg"
        
        if self.parser in (int, float, str, bool):
            type_name = self.parser.__name__
        elif self.parser_name:
            type_name = self.parser_name
        else:
            type_name = "custom"
            
        required = "?" if not self.required else ""
        
        if self.kind == 'kwarg':
            return f"{name}{required}={type_name}"
        else:
            return f"{name}{required}:{type_name}"
        

class CommandSchema(BaseModel):
    arguments: list[CommandArgument] = []
    call: Callable[..., Any] = lambda: None

    @model_validator(mode="after")
    def check_required_order(cls, values):
        seen_optional = False
        for arg in values.arguments:
            if not arg.required:
                seen_optional = True
            elif seen_optional and arg.required:
                raise ValueError("Required arguments cannot follow optional arguments")
        return values

    @property
    def arg_map(self):
        return {arg.name: arg for arg in self.arguments if arg.name}
    
    def __repr__(self):
        posargs = map(repr, filter(lambda arg: arg.kind == 'posarg' and arg.name, self.arguments))
        kwargs = map(repr, filter(lambda arg: arg.kind == 'kwarg' and arg.name, self.arguments))
        allargs = list(posargs) + list(kwargs)
        return f"{' '.join(allargs)} @/"

class Command(BaseModel):
    name: str
    description: str | None = None
    possible_schemas: List[CommandSchema] = []

    def wrap(self, obj):
        if obj['command'] != self.name:
            raise ValueError(f"Command name mismatch: expected {self.name}, got {obj['command']}")

        for schema in self.possible_schemas:
            try:
                parsed_args = self.parse_schema(obj['args'], schema)
            except ValueError as e:
                continue

            if any(arg.required and arg.name not in parsed_args for arg in schema.arguments):
                continue

            return lambda: schema.call(**parsed_args)

        raise ValueError("No matching schema found for command arguments")

    def parse_kwarg(self, schema, arg, has_seen_kwargs):
        has_seen_kwargs = True
        arg_name = arg.get('name')
        arg_value = arg.get('value')

        if arg_name is None or arg_value is None:
            raise ValueError("Invalid keyword argument format")
        if arg_name not in schema.arg_map:
            raise ValueError(f"Unexpected keyword argument: {arg_name}")

        schema_arg = schema.arg_map[arg_name]

        return schema_arg, arg_name, arg_value, has_seen_kwargs

    def parse_posarg(self, schema, arg, has_seen_kwargs, index):
        if has_seen_kwargs:
            raise ValueError("Positional arguments cannot follow keyword arguments")
        if index >= len(schema.arguments):
            raise ValueError("Too many positional arguments")
        schema_arg = schema.arguments[index]
        if schema_arg.kind != 'posarg':
            raise ValueError(f"Expected positional argument, got keyword argument: {schema_arg.name}")
        return schema_arg, schema_arg.name, arg, index + 1

    def parse_schema(self, args, schema):
        has_seen_kwargs = False
        index = 0
        parsed_args = {}

        for arg in args:
            schema_arg = None
            arg_name = None
            arg_value = None

            if isinstance(arg, dict):
                schema_arg, arg_name, arg_value, has_seen_kwargs = \
                    self.parse_kwarg(schema, arg, has_seen_kwargs)
            else:
                schema_arg, arg_name, arg_value, index = \
                    self.parse_posarg(schema, arg, has_seen_kwargs, index)

            if schema_arg is None:
                raise ValueError("Could not determine schema argument")
            elif schema_arg.kind == 'posarg' and isinstance(arg, dict):
                raise ValueError(f"Expected positional argument, got keyword argument: {arg_name}")
            elif schema_arg.kind == 'kwarg' and not isinstance(arg, dict):
                raise ValueError(f"Expected keyword argument, got positional argument: {arg_value}")

            # parse the argument using schema_arg's parser
            try:
                arg_value = schema_arg.parser(arg_value)
            except Exception as e:
                raise ValueError(f"Failed to parse argument {arg_name}: {e}")

            parsed_args[arg_name] = arg_value

        return parsed_args
