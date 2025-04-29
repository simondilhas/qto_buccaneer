import yaml

class SafeLoader(yaml.SafeLoader):
    """Custom YAML loader that handles both scalar and sequence nodes."""
    def construct_scalar(self, node):
        if isinstance(node, yaml.SequenceNode):
            return [self.construct_scalar(child) for child in node.value]
        return super().construct_scalar(node)

    def construct_python_float(self, node):
        return float(self.construct_scalar(node))

    def construct_python_int(self, node):
        return int(self.construct_scalar(node))

# Add constructors for numpy types (for backward compatibility)
SafeLoader.add_constructor('tag:yaml.org,2002:python/object/apply:numpy._core.multiarray.scalar', 
    lambda loader, node: float(loader.construct_scalar(node)))
SafeLoader.add_constructor('tag:yaml.org,2002:python/object/apply:numpy.float64', 
    lambda loader, node: float(loader.construct_scalar(node)))
SafeLoader.add_constructor('tag:yaml.org,2002:python/object/apply:numpy.int64', 
    lambda loader, node: int(loader.construct_scalar(node)))

class NumpySafeDumper(yaml.SafeDumper):
    """Custom YAML dumper that handles numpy types."""
    def represent_scalar(self, tag, value, style=None):
        if isinstance(value, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                            np.uint8, np.uint16, np.uint32, np.uint64)):
            return super().represent_scalar('tag:yaml.org,2002:int', int(value))
        elif isinstance(value, (np.float_, np.float16, np.float32, np.float64)):
            return super().represent_scalar('tag:yaml.org,2002:float', float(value))
        return super().represent_scalar(tag, value, style) 