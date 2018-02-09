""" Slightly less terrible error handling and reporting """
from __future__ import print_function
import sys
import traceback


def unhandled(exception, opt):
    """ Handle uncaught/unexpected errors and be polite about it"""
    exmod = type(exception).__module__
    name = "%s.%s" % (exmod, type(exception).__name__)
    # this is a Vault error
    if exmod == 'aomi.exceptions' or exmod == 'cryptorito':
        # This may be set for Validation or similar errors
        if hasattr(exception, 'source'):
            output(exception.message, opt, extra=exception.source)
        else:
            output(exception.message, opt)

    else:
        output("Unexpected error: %s" % name, opt)

    sys.exit(1)


def output(message, opt, extra=None):
    """ Politely display an unexpected error"""
    print(message, file=sys.stderr)
    if opt.verbose:
        if extra:
            print(extra)

        traceback.print_exc(sys.stderr)
