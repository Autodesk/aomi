"""Exception definitions for aomi"""


class AomiError(Exception):
    """Our generic exception. Builds up an appropriate error message for
    representation to the user"""
    catmsg = None

    def __init__(self, message=None):
        msg = None
        if self.catmsg is not None and message is not None:
            msg = "%s - %s" % (self.catmsg, message)
        elif self.catmsg is not None:
            msg = self.catmsg
        elif message is not None:
            msg = message

        if msg is not None:
            super(AomiError, self).__init__(msg)
        else:
            super(AomiError, self).__init__()


class AomiCredentials(AomiError):
    """This exception is used for representing errors related to authenticating
    against a running Vault server"""
    catmsg = 'Something wrong with Vault credentials'


class AomiData(AomiError):
    """Some kind of aomi specific data is invalid"""
    catmsg = 'Invalid aomi data'


class AomiCommand(AomiError):
    """Invalid interaction attempted with the aomi cli"""
    catmsg = 'Problem with command line arguments'


class AomiFile(AomiError):
    """Something is wrong with a file on the local filesystem"""
    catmsg = 'Problem with a local file'


class VaultConstraint(AomiError):
    """Vault is imposing constraints on us. Permission or pathing generally"""
    catmsg = 'A Vault Constraint Exists'


class KeybaseAPI(AomiError):
    """Covers errors related to the keybase API"""
    catmsg = 'Something wrong with Keybase integration'


class GPG(AomiError):
    """Covers errors related to our GPG wrapper"""
    catmsg = 'Something went wrong interacting with GPG'


class IceFile(AomiError):
    """Something is wrong with an aomi generated icefile"""
    catmsg = 'Corrupt Icefile'


class VaultData(AomiError):
    """Something is wrong with data received from Vault. Usually
    indicates aomi trying to interact with something manually created"""
    catmsg = 'Unexpected Vault Data Woe'


class Validation(AomiError):
    """Some kind of validation failed. Invalid string, length,
    who knows. Never trust user input tho."""
    catmsg = 'Validation Error'
