"""Tool package init: imports all 11 domain modules to trigger @mcp.tool() registration (FR-29, ADR-007).

Importing this package causes all 36 tool functions to register with the FastMCP instance
via their @mcp.tool() decorators. The server asserts the expected count at startup.
"""

from amocrm_mcp.tools import account  # noqa: F401 -- 3 tools
from amocrm_mcp.tools import analytics  # noqa: F401 -- 3 tools
from amocrm_mcp.tools import associations  # noqa: F401 -- 2 tools
from amocrm_mcp.tools import batch  # noqa: F401 -- 3 tools
from amocrm_mcp.tools import companies  # noqa: F401 -- 4 tools
from amocrm_mcp.tools import contacts  # noqa: F401 -- 4 tools
from amocrm_mcp.tools import leads  # noqa: F401 -- 5 tools
from amocrm_mcp.tools import notes  # noqa: F401 -- 2 tools
from amocrm_mcp.tools import pipelines  # noqa: F401 -- 3 tools
from amocrm_mcp.tools import tasks  # noqa: F401 -- 4 tools
from amocrm_mcp.tools import unsorted  # noqa: F401 -- 3 tools
