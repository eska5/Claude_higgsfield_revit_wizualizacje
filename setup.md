# Install Revit, then connect Claude and Cursor

Do this once. After it works, each folder in this repo is one workflow from [AI Architecture Lab](https://archaiflow.com/research). Revit stays open with a model loaded. Claude or Cursor talks to that model through the Revit MCP.

## 1. Install Revit 2027

1. Sign in at [manage.autodesk.com](https://manage.autodesk.com/).
2. Open **Products and services**, find **Revit**, and install **Revit 2027**.
3. Use the full Revit product. Revit LT cannot run the MCP.

Product page: [autodesk.com/products/revit](https://www.autodesk.com/products/revit/overview).

## 2. Open a sample model

The articles use two models that ship with Revit 2027.

| Model | Used for |
| --- | --- |
| Snowdon Towers Sample Architectural | Walkthrough, InDesign deck, After Effects |
| Pacific Continental Residence | Website, Notion booklet, Photoshop looks |

On a default install they are here:

`C:\Program Files\Autodesk\Revit 2027\Samples`

Copy that folder to Documents before you open anything. A save inside `Program Files` overwrites the originals. Keep the Snowdon files together. Architecture, structure, facades, site, HVAC, plumbing, and electrical share one origin.

If Samples is missing, download the files from Autodesk’s sample list and open them in Revit 2027:

[Revit 2027 sample project files](https://help.autodesk.com/cloudhelp/2027/ENU/Revit-GetStarted/files/GUID-61EF2F22-3A1F-4317-B925-1E85F138BE88.htm)

Open **Snowdon Towers Sample Architectural.rvt** for the first test. File → Open, or Ctrl+O.

## 3. Install the Revit connection

Claude and Cursor both talk to the pyRevit extension `revit-mcp-python`. Setup video and the short version live at [archaiflow.com/setup](https://archaiflow.com/setup). The server itself is [revit-mcp-python](https://github.com/revit-mcp/revit-mcp-python).

### pyRevit

1. Download the first installer from [pyrevitlabs.github.io/pyRevit](https://pyrevitlabs.github.io/pyRevit/). Skip the one marked Admin / All Users.
2. Run it with **Core Tools** and **Extended Extensions** ticked.
3. Open Revit. Choose **Always Load** if it asks.

### uv

In PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close that window, open a new one, and run `uv --version`. You should see a version number.

### The extension, inside Revit

1. pyRevit tab → the small pyRevit button at the bottom left.
2. **Extensions**. Search `mcp`. Install **MCP Server for Revit Python** until it says Enabled. On this computer the folder is `%APPDATA%\pyRevit\Extensions\mcp-server-for-revit-python.extension`.
3. **Settings → Routes**. Tick **Routes Server**. Save and reload. An orange band means it is listening, normally at `http://localhost:48884/`.
4. Close Revit and open it again with the sample model.
5. In Revit choose **MCP → Bridge → Connect**. That pairs this Windows user with the server. Requests that change the model stop for review inside Revit.

## 4. Connect Claude

Install [Claude Desktop](https://claude.com/download). In a new chat, paste:

```text
Connect yourself to Revit for me. I am on Windows, with pyRevit, uv
and the MCP extension already installed. Find where they are on
this computer, add the Revit connector to my Claude settings file,
and tell me when to restart Claude.
```

Quit Claude completely, including the system tray, and open it again.

The file it edits is `%APPDATA%\Claude\claude_desktop_config.json`. The shape from the server README is:

```json
{
  "mcpServers": {
    "Revit Connector": {
      "command": "C:\\Users\\USER\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--frozen",
        "--directory",
        "C:\\Users\\USER\\AppData\\Roaming\\pyRevit\\Extensions\\mcp-server-for-revit-python.extension",
        "mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

Those are the paths on this computer. Claude Desktop is not installed here yet, so this entry has not been tried in Claude. Windows paths in JSON need doubled backslashes.

Click **+** under the message box, then **Connectors**. Revit Connector should be on. With the model open, ask:

```text
Can you control my Revit model?
```

A live connection answers with the open file name.

Extra connectors, switched on in that same **+** menu only for the workflow that needs them:

| Connector | Where | Used by |
| --- | --- | --- |
| Higgsfield | Custom connector, URL `https://mcp.higgsfield.ai/mcp`, then sign in | Video walkthrough, Home Tour |
| Adobe | **+ → Connectors → Add connector → Browse connectors**, search Adobe | InDesign deck, Photoshop looks |
| Notion | Same browse list, sign in | Notion to InDesign |
| InDesign MCP | Separate local server. Steps are in the InDesign folder | Booklet that is built on the open InDesign file |

After Effects has no connector. That workflow uses Claude Code and a script. See `revit-to-after-effects/guide.md`.

## 5. Connect Cursor

Cursor uses the same server. Create or edit `%USERPROFILE%\.cursor\mcp.json`:

```json
{
  "mcpServers": {
    "revit": {
      "command": "C:\\Users\\USER\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--frozen",
        "--directory",
        "C:\\Users\\USER\\AppData\\Roaming\\pyRevit\\Extensions\\mcp-server-for-revit-python.extension",
        "mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

This is the file on this computer, and it was tested: the server starts and lists 20 tools. Cursor picked it up without a restart. In Settings → MCP, `revit` should be connected. Revit must be open on the model, with **MCP → Bridge → Connect** already done.

Ask in this chat, with the model open: “What is the title of the Revit model I have open?” The answer should be the file name, read from Revit.

Higgsfield in Cursor is the same URL if a workflow needs images or video from here:

```json
"Higgsfield": {
  "url": "https://mcp.higgsfield.ai/mcp"
}
```

Sign in when Cursor prompts. The walkthrough, the deck, the booklet, the home tour, and the Photoshop looks were run in Claude Desktop or Claude Code. Cursor is the place to edit the site, the scripts, and the exported files those runs leave behind.

## 6. If the model name does not come back

- Revit is open and **MCP → Bridge → Connect** has been clicked this session.
- pyRevit → Settings → Routes shows the orange band.
- pyRevit → Extensions shows the mcp row as Enabled.
- `uv --version` works in a new PowerShell window.
- Claude was fully quit, then reopened. Cursor was restarted after the JSON change.
- The `main.py` path in the JSON exists. Search for it under `%APPDATA%\pyRevit\Extensions` if the folder name differs.

## 7. Which folder to open next

| Folder | Article |
| --- | --- |
| [a-video-walk-through-your-own-revit-model](a-video-walk-through-your-own-revit-model/guide.md) | [A video walk through your own Revit model](https://archaiflow.com/research/revit-fbx-walkthrough) |
| [revit-to-indesign](revit-to-indesign/guide.md) | [Revit to InDesign](https://archaiflow.com/research/revit-indesign-deck) |
| [revit-to-notion-to-indesign](revit-to-notion-to-indesign/guide.md) | [Revit to Notion to InDesign](https://archaiflow.com/research/revit-notion-indesign) |
| [revit-to-website](revit-to-website/guide.md) | [Revit to Website](https://archaiflow.com/research/revit-website) |
| [revit-to-home-tour](revit-to-home-tour/guide.md) | [Revit to Home Tour](https://archaiflow.com/research/revit-home-tour) |
| [revit-to-after-effects](revit-to-after-effects/guide.md) | [Revit to After Effects](https://archaiflow.com/research/revit-after-effects) |
| [photoshop-looks-six-at-once](photoshop-looks-six-at-once/guide.md) | [Photoshop Looks, Six at Once](https://archaiflow.com/research/revit-photoshop-looks) |

Figures in those folders are from those pages, published by David at AI Architecture Lab. Finish [setup](setup.md) before you paste a prompt.
