"""Drop-in replacement for distutils.version (removed in Python 3.12)."""
import re

try:
    # Use the real thing when it exists (Python <= 3.11)
    from distutils.version import LooseVersion, StrictVersion
except ImportError:
    def _parse_version(v):
        return tuple(int(p) if p.isdigit() else p
                     for p in re.split(r'[.\-+]', str(v)) if p)

    class LooseVersion:
        def __init__(self, vstring):
            self.vstring = str(vstring)
            self.version = _parse_version(vstring)

        def _cmp(self, other):
            if not isinstance(other, LooseVersion):
                other = LooseVersion(other)
            a, b = self.version, other.version
            try:
                return (a > b) - (a < b)
            except TypeError:
                # mixed int/str components: compare as strings
                a = tuple(str(x) for x in a)
                b = tuple(str(x) for x in b)
                return (a > b) - (a < b)

        def __eq__(self, o): return self._cmp(o) == 0
        def __lt__(self, o): return self._cmp(o) < 0
        def __le__(self, o): return self._cmp(o) <= 0
        def __gt__(self, o): return self._cmp(o) > 0
        def __ge__(self, o): return self._cmp(o) >= 0
        def __hash__(self): return hash(self.version)
        def __repr__(self): return "LooseVersion('%s')" % self.vstring

    StrictVersion = LooseVersion

__all__ = ["LooseVersion", "StrictVersion"]