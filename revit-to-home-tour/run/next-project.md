# Next building: one pass from Revit to the page

Read this before starting a second project. The Snowdon Towers v2 page
(`run/sales-page-v2/`) is the reference. Copy that folder, do not edit it.
v1 in `run/sales-page/` stays as the before/after comparison.

One command reports what is still missing and, when the inputs exist, rebuilds
the page data and the web-sized media:

```text
python tour_status.py            what is present, what is missing
python tour_status.py --build    overlays, data.js, then web assets
```

Run it from `run/v2-work/`. It never calls Higgsfield and never touches Revit.

## Rules that do not change

- Never save the Revit model. Work on copied views named `HT2 …`.
- Tell the user which views were added and that closing without saving removes them.
- Every number and outline on the page comes from the model.
- Show the Higgsfield cost before spending. `use_unlim: false` unless the
  account actually has an unlimited allowance for that model.
- Keep the camera and the building. The model changes light, materials,
  planting, people and cars.

## 1. Read the model

Through the Revit connector, on copies:

- Levels and their elevations.
- Rooms: number, name, level, area, occupancy, location.
- One 16:9 perspective camera each for the aerial, each cut floor, the
  rooftop and the street. Record origin, right, up, forward and the crop
  (`cams_ht2.json`).
- Two interior cameras per home (`room_cams.json`), picked from sight lines
  (`pick_room_cams.py` once `rays_L*.json` exist).
- Export each camera as a 1920 px PNG into `v2-work/revit/`.

`execute_revit_code` is IronPython 2.7 and the request times out at 60 s
while the export keeps running. Poll the output folder instead of re-running
it. Use `ElementId.Value`.

Write `rooms.json` in the shape `proj.homes()` expects. That filter treats a
room as a home when `occupancy` starts with `Residential` and the number is
not `106` (the Snowdon lobby). Change the filter for a building that numbers
its homes differently.

## 2. Prove the overlays before spending credits

```text
python build_overlays.py
python check_overlay.py
```

`build_overlays.py` renders a depth buffer through the aerial camera. Indoor
rooms stack up to the next level; terraces stay on their own level; the roof
garden is a cap that hides the floors under it.

Two measurements that were wrong the first time:

- The street camera's crop rectangle sits 0.1 ft in front of the eye, not at
  `-cmax.z`. `build_site_data.py` already overrides that for the hotspots.
- Check which way the rooftop camera faces before writing its prompt. On
  Snowdon it faces the street, so a river behind the bandstand was wrong and
  had to be regenerated.

## 3. Stills, then video

Generate stills first and check them. Video spends far more, and a wrong
still means every clip made from it is wrong too.

Stills: an edit model that takes the Revit export as a reference and keeps
the framing (Nano Banana Pro, role `image_references`, 4k, on this run).
Same camera for the five times of day and for each cut, so the overlays stay
put.

Video: Kling 4.0, `image-to-video`, 1080p, 16:9. It keeps the start frame
registered (measured: scale about 0.997, drift of a couple of pixels).
Seedance 2.5 re-framed the hero and was rejected; measure a new model with
`align_check.py` against the hero before using it for anything that carries
an overlay.

Prompt shape that worked:

- Hero and time-of-day loops: locked camera, cars driving, people small,
  no cuts.
- Aerial to a cut: the roof lifts off and the camera settles on that floor.
- Aerial to rooftop or street: one continuous move, start frame is the hero,
  end frame is that still.
- Interior: a slow push from the Revit view. Say the staging is illustrative.
- Time-lapse: one clip from dawn through night, camera locked, 12 s.

Batches of at most 12. Poll with `jobs_wait` (15 s, then again). Record every
job in `jobs.json` under `stills`, `rooms`, `videos` or `roomclips`, then:

```text
python dl.py HHMMSS:idprefix --date YYYYMMDD
```

`dl.py` rebuilds the download URL from `jobs.json` and that timestamp. The
URL pattern in that file is account-specific; do not commit `dl.py` or
`jobs.json`.

File names the page expects, all inside `v2-work/hf/`:

```text
aerial-dawn.png  aerial-noon.png  aerial-golden.png  aerial-dusk.png  aerial-night.png
cut-l5.png  cut-l4.png  cut-l3.png  cut-l2.png  rooftop.png  street.png
hero-kling.mp4  loop-dawn.mp4  loop-noon.mp4  loop-golden.mp4  loop-night.mp4
loop-cut-l5.mp4  loop-cut-l4.mp4  loop-cut-l3.mp4  loop-cut-l2.mp4
loop-rooftop.mp4  loop-street.mp4
to-cut-l5.mp4  to-cut-l4.mp4  to-cut-l3.mp4  to-cut-l2.mp4
l5-to-l4.mp4  l4-to-l3.mp4  l3-to-l2.mp4
fly-rooftop.mp4  fly-street.mp4  timelapse.mp4
room-<num>-a.png  room-<num>-b.png
clip-in-<num>.mp4  clip-amb-<num>.mp4  clip-ambb-<num>.mp4
```

`tour_status.py` prints this list against the homes in `rooms.json`, so a
building with different home numbers needs no edit there.

## 4. Build and check the page

```text
python tour_status.py --build
python ..\sales-page-v2\serve.py
```

Open `http://localhost:8137`. Click one floor, walk into one home, move the
time-of-day slider, open the rooftop and the street. The page falls back to
still images when a clip will not play, so confirm a `<video>` is actually
playing.

Copy `sales-page-v2/` to a new folder for the new building. Leave the Snowdon
copy in place.

## 5. Publish

`.github/workflows/pages.yml` deploys `run/sales-page-v2/` on a push to
`main` or `cursor/revit-workflow-guides`. Point `path:` at the new folder
when the new building should replace the live site. The repo is public, so
anything committed is visible. Leave raw renders, `jobs.json` and `dl.py`
untracked.
