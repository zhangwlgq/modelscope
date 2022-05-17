# Copyright (c) Alibaba, Inc. and its affiliates.
import inspect

from maas_lib.utils.logger import get_logger

default_group = 'default'
logger = get_logger()


class Registry(object):
    """ Registry which support registering modules and group them by a keyname

    If group name is not provided, modules will be registered to default group.
    """

    def __init__(self, name: str):
        self._name = name
        self._modules = dict()

    def __repr__(self):
        format_str = self.__class__.__name__ + f'({self._name})\n'
        for group_name, group in self._modules.items():
            format_str += f'group_name={group_name}, '\
                f'modules={list(group.keys())}\n'

        return format_str

    @property
    def name(self):
        return self._name

    @property
    def modules(self):
        return self._modules

    def list(self):
        """ logging the list of module in current registry
        """
        for group_name, group in self._modules.items():
            logger.info(f'group_name={group_name}')
            for m in group.keys():
                logger.info(f'\t{m}')
            logger.info('')

    def get(self, module_key, group_key=default_group):
        if group_key not in self._modules:
            return None
        else:
            return self._modules[group_key].get(module_key, None)

    def _register_module(self,
                         group_key=default_group,
                         module_name=None,
                         module_cls=None):
        assert isinstance(group_key,
                          str), 'group_key is required and must be str'
        if group_key not in self._modules:
            self._modules[group_key] = dict()

        if not inspect.isclass(module_cls):
            raise TypeError(f'module is not a class type: {type(module_cls)}')

        if module_name is None:
            module_name = module_cls.__name__

        if module_name in self._modules[group_key]:
            raise KeyError(f'{module_name} is already registered in'
                           f'{self._name}[{group_key}]')

        self._modules[group_key][module_name] = module_cls

    def register_module(self,
                        group_key: str = default_group,
                        module_name: str = None,
                        module_cls: type = None):
        """ Register module

        Example:
            >>> models = Registry('models')
            >>> @models.register_module('image-classification', 'SwinT')
            >>> class SwinTransformer:
            >>>     pass

            >>> @models.register_module('SwinDefault')
            >>> class SwinTransformerDefaultGroup:
            >>>     pass

        Args:
            group_key: Group name of which module will be registered,
                default group name is 'default'
            module_name: Module name
            module_cls: Module class object

        """
        if not (module_name is None or isinstance(module_name, str)):
            raise TypeError(f'module_name must be either of None, str,'
                            f'got {type(module_name)}')

        if module_cls is not None:
            self._register_module(
                group_key=group_key,
                module_name=module_name,
                module_cls=module_cls)
            return module_cls

        # if module_cls is None, should return a dectorator function
        def _register(module_cls):
            self._register_module(
                group_key=group_key,
                module_name=module_name,
                module_cls=module_cls)
            return module_cls

        return _register


def build_from_cfg(cfg,
                   registry: Registry,
                   group_key: str = default_group,
                   default_args: dict = None) -> object:
    """Build a module from config dict when it is a class configuration, or
    call a function from config dict when it is a function configuration.

    Example:
        >>> models = Registry('models')
        >>> @models.register_module('image-classification', 'SwinT')
        >>> class SwinTransformer:
        >>>     pass
        >>> swint = build_from_cfg(dict(type='SwinT'), MODELS,
        >>>     'image-classification')
        >>> # Returns an instantiated object
        >>>
        >>> @MODELS.register_module()
        >>> def swin_transformer():
        >>>     pass
        >>>       = build_from_cfg(dict(type='swin_transformer'), MODELS)
        >>> # Return a result of the calling function

    Args:
        cfg (dict): Config dict. It should at least contain the key "type".
        registry (:obj:`Registry`): The registry to search the type from.
        group_key (str, optional): The name of registry group from which
            module should be searched.
        default_args (dict, optional): Default initialization arguments.
    Returns:
        object: The constructed object.
    """
    if not isinstance(cfg, dict):
        raise TypeError(f'cfg must be a dict, but got {type(cfg)}')
    if 'type' not in cfg:
        if default_args is None or 'type' not in default_args:
            raise KeyError(
                '`cfg` or `default_args` must contain the key "type", '
                f'but got {cfg}\n{default_args}')
    if not isinstance(registry, Registry):
        raise TypeError('registry must be an maas_lib.Registry object, '
                        f'but got {type(registry)}')
    if not (isinstance(default_args, dict) or default_args is None):
        raise TypeError('default_args must be a dict or None, '
                        f'but got {type(default_args)}')

    args = cfg.copy()

    if default_args is not None:
        for name, value in default_args.items():
            args.setdefault(name, value)

    obj_type = args.pop('type')
    if isinstance(obj_type, str):
        obj_cls = registry.get(obj_type, group_key=group_key)
        if obj_cls is None:
            raise KeyError(f'{obj_type} is not in the {registry.name}'
                           f'registry group {group_key}')
    elif inspect.isclass(obj_type) or inspect.isfunction(obj_type):
        obj_cls = obj_type
    else:
        raise TypeError(
            f'type must be a str or valid type, but got {type(obj_type)}')
    try:
        return obj_cls(**args)
    except Exception as e:
        # Normal TypeError does not print class name.
        raise type(e)(f'{obj_cls.__name__}: {e}')
