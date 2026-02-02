from typing import Optional

class FormatUtils:
    @staticmethod
    def error(*args):
        msg = " ".join(args)
        return f"\033[91m Error  \033[0m{msg}"

    @staticmethod
    def info(*args):
        msg = " ".join(args)
        return f"\033[94m INFO  \033[0m{msg}"

    @staticmethod
    def success(*args):
        msg = " ".join(args)
        return f"\033[92m Success  \033[0m{msg}"

    @staticmethod
    def warning(*args):
        msg = " ".join(args)
        return f"\033[93m Warning  \033[0m{msg}"

    @staticmethod
    def highlight(text: str, color: Optional[str] = 'yellow') -> str:
        color_code = {
            'yellow': '\033[93m',
            'green': '\033[92m',
            'blue': '\033[94m',
            'red': '\033[91m',
            'reset': '\033[0m'
        }.get(color, '\033[93m')
        return f"{color_code}{text}\033[0m"

    @staticmethod
    def background(text: str, color: Optional[str] = 'yellow') -> str:
        color_code = {
            'yellow': '\033[43m',
            'green': '\033[42m',
            'blue': '\033[44m',
            'red': '\033[41m',
            'reset': '\033[0m'
        }.get(color, '\033[43m')
        return f"{color_code}{text}\033[0m"

    @staticmethod
    def bold(text: str) -> str:
        return f"\033[1m{text}\033[0m"



class PrintUtils:
    def __init__(self):
        pass

    @staticmethod
    def error(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.error(msg), **kwargs)

    @staticmethod
    def info(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.info(msg), **kwargs)

    @staticmethod
    def success(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.success(msg), **kwargs)

    @staticmethod
    def warning(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.warning(msg), **kwargs)


class FormattedText:
    @staticmethod
    def progress(i: int, total: int):
        return f"[{i}/{total}]"

    @staticmethod
    def percent(i: int, total: int):
        return f"[{(i/total)*100:.2f}%]"

def fdebug(title, **kwargs):
    msg = "\n   ".join([
        FormatUtils.background("[DEBUG]", "yellow") + FormatUtils.bold(f" {title}"),
        *[f"- {FormatUtils.highlight(str(k), 'yellow')}={FormatUtils.highlight(repr(v), 'green')}" for k, v in kwargs.items()]
    ])
    return msg