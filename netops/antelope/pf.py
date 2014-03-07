#
"""
Provide a common unified interface for Antelope pf files
"""
import os

try:
    from antelope import stock
except ImportError:
    try:
        import sys
        sys.path.append(os.path.join(os.environ['ANTELOPE'], 'data', 'python'))
        from antelope import stock
    except:
        stock = object()


def get_pf(pfname):
    """Return a dict from a pf file"""
    if hasattr(stock, 'pfread'):
        return stock.pfread(pfname).pf2dict()
    elif hasattr(stock, 'pfget'):
        return stock.pfget(pfname)
    else:
        raise AttributeError("No pf function available")
