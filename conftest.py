"""
Root pytest configuration.

Re-exports every fixture from `tests/conftest.py` (api_client,
create_user, staff_role, etc.) so they're available to every test
package — `apps/accounts/tests/`, `apps/customers/tests/`, and any
app added in later sprints. Without this, fixtures defined under
`tests/` are only visible to tests physically nested under `tests/`,
since pytest scopes conftest.py fixtures to their own directory
subtree, and `tests/` is a sibling of `apps/`, not an ancestor.

(`pytest_plugins = ["tests.conftest"]` looks like the obvious fix but
fails: pytest already auto-imports every conftest.py it discovers
during collection, so re-registering the same module as a named
plugin raises "Plugin already registered under a different name".
A star-import avoids that — it just copies the fixture functions into
this module's namespace, which pytest scans directly.)
"""

from tests.conftest import *  # noqa: F403
