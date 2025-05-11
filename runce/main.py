from typing import TYPE_CHECKING

__version__ = "0.0.0"
if TYPE_CHECKING:
    import argparse
    from typing import Any, Sequence

INVALID = object()


class Argument:
    """CLI argument definition container."""

    def __init__(self, *args: str, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def _add(self, name: str, type_: type, argp: "argparse.ArgumentParser", that: "Any") -> None:
        """Add argument to parser."""
        args = []
        kwargs = {**self.kwargs}
        flag_arg = kwargs.pop("flag", None)

        action = kwargs.get("action")
        const = kwargs.get("const")
        default = kwargs.get("default", INVALID)
        # kind = type(default)
        # print(name, type_, that, "_add", action, flag_arg)

        if action is None:
            if const is not None:
                kwargs["action"] = "append_const" if type_ and issubclass(type_, list) else "store_const"
            elif type_ is None:
                kwargs["action"] = "store"
            elif issubclass(type_, bool):
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
            elif issubclass(type_, list) or isinstance(default, list):
                if "nargs" not in kwargs:
                    kwargs["action"] = "append"
                if "default" not in kwargs:
                    kwargs["default"] = []
            else:
                kwargs["action"] = "store"

        parser = kwargs.pop("parser", None)
        if parser:
            kwargs["type"] = parser
        elif type_ is not bool and issubclass(type_, (int, float, str)):
            kwargs["type"] = type_

        if flag_arg is None:
            for x in self.args:
                if " " in x or "\t" in x:
                    kwargs["help"] = x
                else:
                    if "metavar" not in kwargs:
                        kwargs["metavar"] = x
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


def _arg_fields(inst: "Any") -> "Any":
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

    def __getattr__(self, name: str) -> "Any":
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

    def main(
        self,
        args: "Sequence[str]|None" = None,
        argp: "argparse.ArgumentParser|None" = None,
    ):
        """Main entry point for the command."""
        if argp is None:
            argp = self.new_argparse()
        self.init_argparse(argp)
        self.add_arguments(argp)
        self.parse_arguments(argp, args)
        self.ready()
        self.start()
        self.done()
        return self

    def new_argparse(self) -> "argparse.ArgumentParser":
        """Create a new argument parser."""
        from argparse import ArgumentParser

        return ArgumentParser()

    def init_argparse(self, argp: "argparse.ArgumentParser") -> None:
        """Initialize the argument parser."""
        pass

    def add_arguments(self, argp: "argparse.ArgumentParser") -> None:
        """Add arguments to the parser."""
        for k, v, t in _arg_fields(self):
            v._add(k, t, argp, self)

    def parse_arguments(self, argp: "argparse.ArgumentParser", args: "Sequence[str]|None") -> None:
        """Parse command line arguments."""
        sp = None
        for s, k in self.sub_args():
            if s:
                if sp is None:
                    sp = argp.add_subparsers(required=True)
                s._parent_arg = self
                p = sp.add_parser(k.pop("name"), **k)
                p.set_defaults(_sub_arg=s)
                s.init_argparse(p)
                s.add_arguments(p)

        if sp:
            ns = argp.parse_args(args)
            try:
                s = self._sub_arg = ns._sub_arg
            except AttributeError:
                raise
            else:
                m = ns.__dict__
                while s:
                    for k, v, t in _arg_fields(s):
                        if k in m:
                            setattr(s, k, m[k])
                    q: "Main|None" = getattr(s, "_parent_arg", None)
                    if q:
                        s.ready()
                        s.start()
                        s.done()
                    s = q
        else:
            argp.parse_args(args, self)

    def ready(self) -> None:
        """Called before command execution."""
        pass

    def done(self) -> None:
        """Called after command execution."""
        pass

    def start(self) -> None:
        """Main command execution."""
        pass

    def sub_args(self) -> "Any":
        """Yield subcommands."""
        yield None, {}
