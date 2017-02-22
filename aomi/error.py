""" Slightly less terrible error handling and reporting """
from __future__ import print_function
import sys
import traceback


def unhandled(exception, opt):
    """ Handle uncaught/unexpected errors and be polite about it"""
    exmod = type(exception).__module__
    name = "%s.%s" % (exmod, type(exception).__name__)
    # this is a Vault error
    if exmod == 'aomi.exceptions':
        output(exception.message, opt)
    else:
        output("Unexpected error: %s" % name, opt)


def output(message, opt):
    """ Politely display an unexpected error"""
    print(message, file=sys.stderr)
    if opt.verbose:
        traceback.print_exc(sys.stderr)

    sys.exit(1)
