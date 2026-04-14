from .config import ConfigField
import numbers


__all__ = [
    "Any",
    "String",
    "Integer",
    "Float",
    "Scalar",
    "Bool",
    "Options",
    "MultiOptions",
    "Path",
    "Seed",
    "Range",
    "List",
    "Dict",
    "Date",
    "Time",
    "DateTime"
]


class Options(ConfigField):

    def __init__(self, options, doc, default_value=None, static=False):
        self.options = options
        defaultval = options[0] if default_value is None else default_value
        super().__init__(defaultval, doc, static)

    def validate(self, value):
        if value not in self.options:
            raise ValueError(f"Expected {value} to be one of {self.options}")


class String(ConfigField):

    def __init__(self, default_value, doc, minsize=0, maxsize=None, predicate=None, static=False):
        self.minsize = minsize
        self.maxsize = maxsize
        self.predicate = predicate
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(f"Expected {value} to be an str")
        if len(value) < self.minsize:
            raise ValueError(
                f"Expected {value} to be longer than minimal required length of {self.minsize}"
            )
        if self.maxsize is not None and len(value) > self.maxsize:
            raise ValueError(
                f"Expected {value} to be shorter than maximal allowed length of {self.maxsize}"
            )
        if self.predicate is not None and not self.predicate(value):
            raise ValueError(
                f"Expected {self.predicate}({value}) to be true."
            )


class Scalar(ConfigField):

    def __init__(self, default_value, doc, minval=0, maxval=None, static=False):
        self.minval = minval
        self.maxval = maxval
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, numbers.Number):
            raise TypeError(f"Expected {value!r} to be an scalar quantity")
        if self.minval is not None and value < self.minval:
            raise ValueError(
                f"Expected {value} to be at least {self.minvalue!r}"
            )
        if self.maxval is not None and value > self.maxval:
            raise ValueError(
                f"Expected {value!r} to be no more than {self.maxvalue!r}"
            )
