import tabulate


class ConfigField:

    def __init__(self, default_value, doc, static=False):
        self.defaultval = default_value
        self.doc = doc
        self.static = static
        self.validate(self.defaultval)

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.static:
            return self.defaultval
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        if self.static:
            raise AttributeError("Can not set static config fields.")
        self.validate(value)
        setattr(obj, self.private_name, value)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(name={self.public_name}, "
            f"default={self.defaultval}, {self.doc})"
        )

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"(name={self.public_name}, "
            f"default={self.defaultval}, {self.doc})"
        )

    def validate(self, value):
        return True


class ConfigMeta(type):

    def unroll_defaults(configs):
        conf = {}
        if configs is None:
            return conf
        for cfg in reversed(configs):
            conf.update(cfg.defaults)
        return conf

    def nest_configs(components, defaults):
        nested = {}
        if components is None:
            return nested
        for comp in reversed(components):
            component = comp()
            for k, v in defaults.items():
                if k in component.defaults.keys():
                    setattr(component, k, v.defaultval)
            nested[component.shortname] = component
        return nested

    def __new__(cls, cls_name, bases, attrs, **kwargs):
        cls_config = {attr: val for attr, val in attrs.items() if isinstance(val, ConfigField)}
        components = kwargs.pop("components", None)
        method = kwargs.pop("method", "unroll")
        config = {}
        if "nest" in method:
            config = cls.nest_configs(components, cls_config)
        else:
            config = cls.unroll_defaults(bases)
            cmp_configs = cls.unroll_defaults(components)
            config.update(cmp_configs)
            config.update(cls_config)

        # override any keys that are set in the lowest/latest
        # class in the rung - that's the one user is working with
        config.update(cls_config)
        attrs["defaults"] = config
        attrs.update(config)
        return super().__new__(cls, cls_name, bases, attrs)


class Config(metaclass=ConfigMeta):
    shortname = "conf"

    def __init__(self, **kwargs):
        for k, v in self.defaults.items():
            if not isinstance(v, Config) and not getattr(type(self), k).static:
                setattr(self, k, v.defaultval)
            else:
                self.k = v

    def keys(self):
        return self.defaults.keys()

    def items(self):
        return [(k, getattr(self, k)) for k in self.keys()]

    def values(self):
        return [getattr(self, k) for k in self.keys()]

    def __repr__(self):
        res = f"{self.__class__.__name__}("
        take_away = False
        for k, v in self.items():
            res += f"{k}: {v}, "
            take_away = True
        res = res[:-2] if take_away else res
        return res + ")"

    def __str__(self):
        tbl = {
            "Key": self.keys(),
            "Value": self.values(),
            "Description": [getattr(type(self), attr).doc for attr in self.keys()]
        }
        res = f"{self.__class__.__name__}:\n"
        if self.__class__.__doc__ is not None:
            res += f"{self.__class__.__doc__}\n\n"
        res += tabulate(tbl, headers="keys")
        return res

