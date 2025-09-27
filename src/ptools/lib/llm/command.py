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
    nargs: int | str  = 1 # number of args, or '*' for all remaining

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
        veriadic = "*" if self.nargs == "*" else (f"[{self.nargs}]" if self.nargs > 1 else "")
        
        if self.kind == 'kwarg':
            return f"{name}{required}:{type_name}=<value>"
        else:
            return f"{name}{veriadic}{required}:{type_name}"
        

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

    def wrap(self, obj, context=None) -> Callable[[], Any]:
        if obj['command'] != self.name:
            raise ValueError(f"Command name mismatch: expected {self.name}, got {obj['command']}")

        for schema in self.possible_schemas:
            try:
                parsed_args = self.parse_schema(obj['args'], schema)
            except ValueError as e:
                continue

            if any(arg.required and arg.name not in parsed_args for arg in schema.arguments):
                continue

            return lambda: schema.call(**parsed_args, context=context)

        raise ValueError("No matching schema found for command arguments")

    def parse_kwarg(self, schema, arg, has_seen_kwargs, index):
        has_seen_kwargs = True
        arg_name = arg.get('name')
        arg_value = arg.get('value')

        if arg_name is None or arg_value is None:
            raise ValueError("Invalid keyword argument format")
        if arg_name not in schema.arg_map:
            raise ValueError(f"Unexpected keyword argument: {arg_name}")
        

        schema_arg = schema.arg_map[arg_name]
        if schema_arg.kind != 'kwarg':
            raise ValueError(f"Expected keyword argument, got positional argument: {arg_name}")
        
        if schema_arg.nargs != 1:
            raise ValueError(f"Expected exactly one value for keyword argument: {arg_name}")

        return schema_arg, arg_name, arg_value, has_seen_kwargs, index + 1

    def parse_posarg(self, schema, arg, has_seen_kwargs, index, args):
        if has_seen_kwargs:
            raise ValueError("Positional arguments cannot follow keyword arguments")
        if index >= len(schema.arguments):
            raise ValueError("Too many positional arguments")
        schema_arg = schema.arguments[index]
        if schema_arg.kind != 'posarg':
            raise ValueError(f"Expected positional argument, got keyword argument: {schema_arg.name}")
        
        if schema_arg.nargs == "*" or schema_arg.nargs > 1:
            remaining_posargs = filter(lambda a: not isinstance(a, dict), args[index:])
            if schema_arg.nargs == "*":
                arg = list(remaining_posargs)
                index = len(args)
            else:
                arg = list(remaining_posargs)[:schema_arg.nargs]
                index += schema_arg.nargs
                if len(arg) < schema_arg.nargs:
                    raise ValueError(f"Expected {schema_arg.nargs} values for argument: {schema_arg.name}")
        else:
            arg = arg
            index += 1

        return schema_arg, schema_arg.name, arg, index

    def parse_schema(self, args, schema):
        has_seen_kwargs = False
        parsed_args = {}
        index = 0
        
        while index < len(args):
            arg = args[index]
            schema_arg = None
            arg_name = None
            arg_value = None

            if isinstance(arg, dict):
                schema_arg, arg_name, arg_value, has_seen_kwargs, index = \
                    self.parse_kwarg(schema, arg, has_seen_kwargs, index)
            else:
                schema_arg, arg_name, arg_value, index = \
                    self.parse_posarg(schema, arg, has_seen_kwargs, index, args)

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
