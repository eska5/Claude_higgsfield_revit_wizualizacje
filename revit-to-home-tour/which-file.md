# Which file to open for the Home Tour

Question: which Snowdon Towers download do I open in Revit for [the Home Tour guide](guide.md)?

Answer: **Revit 2027**, file **Architectural**.

1. On the [Revit 2027 sample files page](https://help.autodesk.com/cloudhelp/2027/ENU/Revit-GetStarted/files/GUID-61EF2F22-3A1F-4317-B925-1E85F138BE88.htm), under Snowdon Towers, download **Architectural**.
2. Also download **Facades**, **Structural**, and **Site** into the same folder. The architectural model links those. Leave Electrical, HVAC, Plumbing, and Point Clouds for later.
3. Copy the folder to Documents. Do not work inside `C:\Program Files\Autodesk\Revit 2027\Samples`.
4. Open **Snowdon Towers Sample Architectural.rvt**.

That is the model the Home Tour article uses: homes, areas, and the aerial, street, and rooftop cameras. If Revit warns about missing links, the Facades, Structural, or Site file is not in that same folder.

## Family or model?

Open it as a **model**. The file ends in `.rvt`, so it is a project. Use **File → Open** and choose that file.

A family is an `.rfa` file (a door, a window, a chair). Do not use Open Family or Load Family for Snowdon Towers.

## The three missing links

Manage Links shows a warning on Electrical, Plumbing, and HVAC. Leave them. Facade, Structural, and Site are already loaded, and those are the ones this tour uses. The warning only means those three files are not in the folder. Download them later if you want the full coordinated model.
