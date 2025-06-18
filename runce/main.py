from typing import TYPE_CHECKING

__version__ = "0.0.7"
if TYPE_CHECKING:
    from argparse import ArgumentParser
    from typing import Sequence, Generator

INVALID = object()


class Argument:
    """CLI argument definition container."""

    def __init__(self, *args: str, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def _add(self, name: str, klass: type, argp: "ArgumentParser", that: object) -> None:
        """Add argument to parser."""
        args = []
        kwargs = {**self.kwargs}
        flag_arg = kwargs.pop("flag", None)
        action = kwargs.get("action")
        const = kwargs.get("const")
        default = kwargs.get("default", INVALID)
        kind = klass if isinstance(klass, type) else type

        if action is None:
            if const is not None:
                kwargs["action"] = "append_const" if issubclass(kind, list) or isinstance(default, list) else "store_const"
            elif issubclass(kind, bool):
                if default is None:
                    try:
                        from argparse import BooleanOptionalAction

                        kwargs["action"] = BooleanOptionalAction
                    except ImportError:
                        kwargs["action"] = "store_true"
                elif default is True:
                    kwargs["action"] = "store_false"
                else:
                    assert default is INVALID or default is False
                    kwargs["action"] = "store_true"
            elif issubclass(kind, list) or isinstance(default, list):
                if "nargs" not in kwargs:
                    kwargs["action"] = "append"
                if "default" not in kwargs:
                    kwargs["default"] = []
            else:
                kwargs["action"] = "store"

        parser = kwargs.pop("parser", None)
        if kwargs.get("action") in ("count", "store_const"):
            pass
        elif parser:
            kwargs["type"] = parser
        elif kind is not bool and issubclass(kind, (int, float, str)):
            kwargs["type"] = kind

        if flag_arg is None:
            for x in self.args:
                if " " in x or "\t" in x:
                    kwargs["help"] = x
                else:
                    if "metavar" not in kwargs:
                        kwargs["metavar"] = x.upper()
            if kwargs.pop("required", None) is False:
                kwargs["nargs"] = "?"
        else:

            def add_args(x: str) -> None:
                args.append(x if x.startswith("-") else (f"--{x}" if len(x) > 1 else f"-{x}"))

            for x in self.args:
                if " " in x or "\t" in x:
                    kwargs["help"] = x
                else:
                    add_args(x)

            if not args:
                add_args(name)

        kwargs["dest"] = name
        setattr(that, name, kwargs.get("default"))
        argp.add_argument(*args, **kwargs)


def _arg_fields(inst: object):
    for c in inst.__class__.__mro__:
        for k, v in tuple(c.__dict__.items()):
            if isinstance(v, Argument):
                yield k, v, c.__annotations__.get(k)
            elif isinstance(v, (list, tuple)) and v and isinstance(v[0], Argument):
                for x in v:
                    yield k, x, c.__annotations__.get(k)


def arg(*args: str, **kwargs) -> Argument:
    """Define positional argument."""
    return Argument(*args, **kwargs)


def flag(*args: str, **kwargs) -> Argument:
    """Define flag argument."""
    return Argument(*args, flag=True, **kwargs)


class Main:
    """Base class for all CLI commands."""

    def __getattr__(self, name: str) -> object:
        if not name.startswith("_get_"):
            f = getattr(self, f"_get_{name}", None)
            if f:
                setattr(self, name, None)
                v = f()
                setattr(self, name, v)
                return v
        try:
            m = super().__getattr__
        except AttributeError:
            raise AttributeError(f"{self.__class__.__name__} has no attribute {name}") from None
        else:
            return m(name)

    def main(self, args: "Sequence[str]|None" = None, argp: "ArgumentParser|None" = None):
        """Entry point for CLI execution.
        Args:
            args: Command-line arguments (optional).
            argp: Custom ArgumentParser (optional).
        """
        if argp is None:
            argp = self.new_argparse()
        self.init_argparse(argp)
        self.add_arguments(argp)
        self.parse_arguments(argp, args)
        return self

    def new_argparse(self) -> "ArgumentParser":
        """Create a new argument parser."""
        from argparse import ArgumentParser

        return ArgumentParser()

    def init_argparse(self, argp: "ArgumentParser") -> None:
        """Initialize the argument parser."""
        pass

    def add_arguments(self, argp: "ArgumentParser") -> None:
        """Add arguments to the parser."""
        for k, v, t in _arg_fields(self):
            v._add(k, t, argp, self)

    def ready(self) -> None:
        """Called after arguments are parsed."""
        pass

    def done(self) -> None:
        """Called after command execution."""
        pass

    def start(self) -> None:
        """Main command execution. Called after ready()"""
        pass

    def sub_args(self):
        # type: () -> Generator[tuple[Main|None, dict[str,object]], None, None]
        """Yield subcommands."""
        yield None, {}

    def parse_arguments(self, argp: "ArgumentParser", args: "Sequence[str]|None") -> None:
        """Parse command line arguments."""
        p = self._walk_subparsers(argp)

        if p:
            self._arg_parent = None
            n = argp.parse_args(args)
            s = self._arg_final = n._arg_final
            for k, v in n.__dict__.items():
                setattr(s, k, v)
            s.ready()
            s.start()
            s.done()
        else:
            argp.parse_args(args, self)
            self.ready()
            self.start()
            self.done()

    def _walk_subparsers(self, argp: "ArgumentParser", root=None):
        s = None
        for c, d in self.sub_args():
            if c:
                if s is None:
                    s = argp.add_subparsers(required=True)
                c._arg_parent = self
                p = s.add_parser(d.pop("name"), **d)
                p.set_defaults(_arg_final=c)
                c.init_argparse(p)
                c.add_arguments(p)
                c._walk_subparsers(p)
        return s

    def _arg_parents_and_self(self):
        # type: () -> Generator[Main, object, None]
        c: "Main | None" = self
        while c is not None:
            yield c
            c = c._arg_parent

    def _arg_parents(self):
        # type: () -> Generator[Main, object, None]
        c = self._arg_parent
        while c is not None:
            yield c
            c = c._arg_parent

    _arg_final: "Main | None"
    _arg_parent: "Main | None"
