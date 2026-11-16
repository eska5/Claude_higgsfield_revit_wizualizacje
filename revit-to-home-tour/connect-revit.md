# Connecting to Revit on this computer

Checked on 13 Nov 2026, with Snowdon Towers open in Revit 2027.4.

Decision: **Cursor** talks to Revit. Claude Desktop is not installed here.

| Part | State | Where |
| --- | --- | --- |
| uv | Installed, version 0.13.8 | `C:\Users\USER\.local\bin\uv.exe` |
| pyRevit | Installed, Routes server on | Listening on `127.0.0.1:48884` |
| MCP extension | Installed, but **disabled** in pyRevit | `C:\Users\USER\AppData\Roaming\pyRevit\Extensions\mcp-server-for-revit-python.extension` |
| Pairing | Not done yet | No file at `%LOCALAPPDATA%\RevitMCPPython\pairing.dpapi` |
| Cursor connector | **Done**, named `revit`, 20 tools | `C:\Users\USER\.cursor\mcp.json` |
| Claude Desktop | Not installed | No `%APPDATA%\Claude` folder |

The extension folder is named `mcp-server-for-revit-python.extension` here, not `revit-mcp-python.extension` as in the article. The server file is `main.py` inside it.

The first start downloaded Python 3.13 and the server's packages into a `.venv` folder inside the extension folder.

## Pairing is done, the header was dropped

Connect created `%LOCALAPPDATA%\RevitMCPPython\pairing.dpapi`. A direct status call with that pairing still returned 401, because pyRevit built the route request without copying HTTP headers. The extension then treated every call as unpaired.

Fixed in `pyRevit-Master\pyrevitlib\pyrevit\routes\server\server.py` by copying `self.headers` onto the request. A pyRevit reload keeps the old server code in memory, because that module is imported only once per Revit session. Close Revit completely and open the model again, then ask which model is open. Pairing survives the restart, so Connect does not need to be clicked again.

## To undo

Delete the `revit` entry from `C:\Users\USER\.cursor\mcp.json`. In Revit, **MCP → Bridge → Disconnect** removes the pairing.

## If Claude Desktop is installed later

Install it from [claude.com/download](https://claude.com/download). The connector entry for its settings file is in [setup.md](../setup.md), section 4.
