import unittest
import random
import string
import aomi.model.auth

def random_string(length):
  return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def generate_tokenrole_object():
  return {
    "name": random_string(32),
    "orphan": False,
    "period": random.randint(0, 9999),
    "renewable": False,
    "explicit_max_ttl": random.randint(0, 9999),
    "path_suffix": random_string(32)
  }

class GeneratedTokenRoleTest(unittest.TestCase):
  """GeneratedTokenRoleTest"""

  def test_new_tokenrole(self):
    authbackend = aomi.model.auth

    test_obj = generate_tokenrole_object()

    tokenrole = authbackend.TokenRole(test_obj, {})
    assert tokenrole.role_name == test_obj['name']
    assert tokenrole.path == ("auth/token/roles/%s" % test_obj['name'])

  def test_diff_tokenrole(self):
    authbackend = aomi.model.auth

    NOOP = 0
    CHANGED = 1
    ADD = 2
    DEL = 3
    OVERWRITE = 4

    test_obj_a = generate_tokenrole_object()
    
    tokenrole_a = authbackend.TokenRole(test_obj_a, {})

    # test for adding
    assert tokenrole_a.existing == None
    assert tokenrole_a.diff() == ADD

    # test for not changing
    del test_obj_a['name']
    tokenrole_a.existing = test_obj_a
    assert tokenrole_a.diff() == NOOP

    # test for changing
    test_obj_b = generate_tokenrole_object()
    del test_obj_b['name']
    tokenrole_a._obj = test_obj_b # mutate token role
    assert tokenrole_a.diff() == CHANGED

    # test for deleting
    tokenrole_a._obj = {}
    tokenrole_a.present = False
    assert tokenrole_a.diff() == DEL
