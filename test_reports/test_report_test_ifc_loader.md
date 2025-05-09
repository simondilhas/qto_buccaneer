# Test Execution Report

## Summary

- Total tests: 11
- Passed: 7
- Failed: 4
- Skipped: 0

## Failed Tests Analysis

### test_get_element_spatial_relationship

**Problem**: Assertion failed

**Error**: tests\test_ifc_loader.py:199: AssertionError

**Details**:

- E        +  where 1 = len(     GlobalId BuildingStory  ElevationOfStory\n0  SPACE_ID_1  Ground Floor               0.0)

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_get_entity_metadata_df

**Problem**: Key not found in DataFrame

**Error**: except (AttributeError, KeyError):

**Explanation**: The filter expression parser is not handling complex expressions correctly.

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_get_entity_geometry_df

**Problem**: Key not found in DataFrame

**Error**: except (AttributeError, KeyError):

**Explanation**: The filter expression parser is not handling complex expressions correctly.

**Suggested Fix**: Update the implementation to correctly handle these cases.

### test_get_filtered_elements

**Error Details**:
```
ifc_loader = <qto_buccaneer.utils.ifc_loader.IfcLoader object at 0x000001B94B3C5750>

    def test_get_filtered_elements(ifc_loader):
        """Test getting filtered elements."""
        # Mock the filter_elements method
>       with patch('qto_buccaneer.utils.ifc_loader.IfcFilter.filter_elements', return_value=pd.DataFrame([{"GlobalId": "ID1"}])):

tests\test_ifc_loader.py:235: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\AppData\Local\Programs\Python\Python311\Lib\unittest\mock.py:1430: in __enter__
    self.target = self.getter()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

name = 'qto_buccaneer.utils.ifc_loader.IfcFilter'

    def resolve_name(name):
        """
        Resolve a name to an object.
    
        It is expected that `name` will be a string in one of the following
        formats, where W is shorthand for a valid Python identifier and dot stands
        for a literal period in these pseudo-regexes:
    
        W(.W)*
        W(.W)*:(W(.W)*)?
    
        The first form is intended for backward compatibility only. It assumes that
        some part of the dotted name is a package, and the rest is an object
        somewhere within that package, possibly nested inside other objects.
        Because the place where the package stops and the object hierarchy starts
        can't be inferred by inspection, repeated attempts to import must be done
        with this form.
    
        In the second form, the caller makes the division point clear through the
        provision of a single colon: the dotted name to the left of the colon is a
        package to be imported, and the dotted name to the right is the object
        hierarchy within that package. Only one import is needed in this form. If
        it ends with the colon, then a module object is returned.
    
        The function will return an object (which might be a module), or raise one
        of the following exceptions:
    
        ValueError - if `name` isn't in a recognised format
        ImportError - if an import failed when it shouldn't have
        AttributeError - if a failure occurred when traversing the object hierarchy
                         within the imported package to get to the desired object.
        """
        global _NAME_PATTERN
        if _NAME_PATTERN is None:
            # Lazy import to speedup Python startup time
            import re
            dotted_words = r'(?!\d)(\w+)(\.(?!\d)(\w+))*'
            _NAME_PATTERN = re.compile(f'^(?P<pkg>{dotted_words})'
                                       f'(?P<cln>:(?P<obj>{dotted_words})?)?$',
                                       re.UNICODE)
    
        m = _NAME_PATTERN.match(name)
        if not m:
            raise ValueError(f'invalid format: {name!r}')
        gd = m.groupdict()
        if gd.get('cln'):
            # there is a colon - a one-step import is all that's needed
            mod = importlib.import_module(gd['pkg'])
            parts = gd.get('obj')
            parts = parts.split('.') if parts else []
        else:
            # no colon - have to iterate to find the package boundary
            parts = name.split('.')
            modname = parts.pop(0)
            # first part *must* be a module/package.
            mod = importlib.import_module(modname)
            while parts:
                p = parts[0]
                s = f'{modname}.{p}'
                try:
                    mod = importlib.import_module(s)
                    parts.pop(0)
                    modname = s
                except ImportError:
                    break
        # if we reach this point, mod is the module, already imported, and
        # parts is the list of parts in the object hierarchy to be traversed, or
        # an empty list if just the module is wanted.
        result = mod
        for p in parts:
>           result = getattr(result, p)
E           AttributeError: module 'qto_buccaneer.utils.ifc_loader' has no attribute 'IfcFilter'

..\..\..\..\AppData\Local\Programs\Python\Python311\Lib\pkgutil.py:715: AttributeError
```

**Suggested Fix**: Update the implementation to correctly handle these cases.
