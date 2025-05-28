from typing import TYPE_CHECKING

__version__ = "0.0.4"
if TYPE_CHECKING:
    import argparse
    from typing import Sequence, Generator, Any

INVALID = object()


class Argument:
    """CLI argument definition container."""

    def __init__(self, *args: str, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def _add(self, name: str, type_: type, argp: "argparse.ArgumentParser", that: object) -> None:
        """Add argument to parser."""
        args = []
        kwargs = {**self.kwargs}
        flag_arg = kwargs.pop("flag", None)
        action = kwargs.get("action")
        const = kwargs.get("const")
        default = kwargs.get("default", INVALID)

        if action is None:

            if const is not None:
                kwargs["action"] = "append_const" if issubclass(type_, list) or isinstance(default, list) else "store_const"
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
        if kwargs.get("action") == "count":
            pass
        elif parser:
            kwargs["type"] = parser
        elif type_ is not bool and type(type_) is type and issubclass(type_, (int, float, str)):
            kwargs["type"] = type_
        # print(name, type_, that, "_add", action, flag_arg)
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

    def main(
        self,
        args: "Sequence[str]|None" = None,
        argp: "argparse.ArgumentParser|None" = None,
    ):
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
        # type: () -> Generator[tuple[Main|None, dict[str,Any]], None, None]
        """Yield subcommands."""
        yield None, {}

    def parse_arguments(self, argp: "argparse.ArgumentParser", args: "Sequence[str]|None") -> None:
        """Parse command line arguments."""
        p = self._walk_subparsers(argp)

        if p:
            self._arg_parent = None
            n = argp.parse_args(args)
            try:
                s = self._arg_final = n._arg_final
            except AttributeError:
                raise
            else:
                m, h, a = n.__dict__, None, s
                while a:
                    h = (a, h)
                    for k, v, t in _arg_fields(a):
                        if k in m:
                            setattr(a, k, m[k])
                    a = getattr(a, "_arg_parent", None)
                assert h and h[0] is self
                s._arg_parent_head = h
                for m in s._arg_parents_and_self():
                    m.ready()
                for m in s._arg_parents_and_self():
                    m.start()
                for m in s._arg_parents_and_self():
                    m.done()
        else:
            argp.parse_args(args, self)
            self.ready()
            self.start()
            self.done()

    def _walk_subparsers(self, argp: "argparse.ArgumentParser", root=None):
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
        # type: () -> Generator[Main, Any, Any]
        c = self._arg_parent_head
        while c is not None:
            d, n = c
            yield d
            c = n

    def _arg_parents(self):
        for d in self._arg_parents_and_self():
            if d is self:
                break
            yield d

    _arg_final: "Main | None"
    _arg_parent: "Main | None"
    _arg_parent_head: "tuple[Main, tuple] | None"
