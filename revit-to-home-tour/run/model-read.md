# What the model has

Read from **Snowdon Towers Sample Architectural v2** on 13 Nov 2026, through the Revit connector. Nothing in the model was changed. Areas are square feet, as Revit reports them.

## Counts

| What | Count |
| --- | --- |
| Levels | 18 |
| Rooms | 54 |
| Homes | 21, on 4 levels (L2 to L5) |
| 3D views | 36 |
| Perspective cameras among them | 20 |

The model's own schedule, "Live/Work Units (by Type)", also totals 21.

## Levels

| Level | Elevation (ft) |
| --- | --- |
| Parking | -16.92 |
| L1 - Block 35 | -5.92 |
| L1 - Block 37 | -3.46 |
| L1 - Block 43 | 0.00 |
| M1 | 5.50 |
| L2 | 8.08 |
| L3 | 18.83 |
| L4 | 32.17 |
| L5 | 45.50 |
| Block 37 - Parapet | 47.67 |
| Block 43 - Parapet | 51.17 |
| R1 | 52.67 |
| Block 39 - Parapet | 54.67 |
| R2 | 58.83 |
| Green Roof Hardscape | 59.92 |
| Parapet | 63.50 |
| R3 | 68.83 |
| Parapet 2 | 70.83 |

## Homes

A home is a room whose occupancy is "Residential One Story" or "Residential Two Story".

| Level | Number | Type | Area (sq ft) |
| --- | --- | --- | --- |
| L2 | 202 | Live/Work Unit | 838.87 |
| L2 | 203 | Studio Unit | 592.88 |
| L2 | 204 | Two Story Studio Unit | 569.39 |
| L2 | 205 | Live/Work Unit | 1105.16 |
| L3 | 303 | Live/Work Unit | 839.50 |
| L3 | 304 | Studio Unit | 592.88 |
| L3 | 306 | Live/Work Unit | 1145.41 |
| L3 | 307 | Live/Work Unit | 1105.16 |
| L3 | 308 | Live/Work Unit | 583.11 |
| L3 | 309 | Live/Work Unit | 766.00 |
| L4 | 403 | Live/Work Unit | 839.88 |
| L4 | 404 | Studio Unit | 592.88 |
| L4 | 405 | Live/Work Loft Unit | 722.91 |
| L4 | 406 | Two Story Studio Unit | 570.27 |
| L4 | 407 | Live/Work Unit | 1145.74 |
| L4 | 408 | Live/Work Unit | 1105.16 |
| L4 | 409 | Live/Work Unit | 582.91 |
| L4 | 410 | Live/Work Unit | 767.60 |
| L5 | 504 | Studio Unit | 592.88 |
| L5 | 506 | Live/Work Unit | 1105.16 |
| L5 | 507 | Live/Work Unit | 914.52 |

By level: L2 has 4, L3 has 6, L4 has 8, L5 has 3.

By type: 14 Live/Work Unit, 4 Studio Unit, 2 Two Story Studio Unit, 1 Live/Work Loft Unit.

Largest home: 407, 1145.74 sq ft. Smallest: 204, 569.39 sq ft.

Home 507 also has a Private Patio, room 507A, 204.10 sq ft.

## Shared and street-level rooms the page can use

| Number | Name | Level | Area (sq ft) |
| --- | --- | --- | --- |
| R100 | Green Roof | Green Roof Hardscape | 5177.49 |
| R101 | Bandstand | Green Roof Hardscape | 734.16 |
| 503 | Green Roof | L5 | 304.06 |
| 505 | Green Roof | L5 | 804.00 |
| 106 | Residential Lobby | L1 - Block 37 | 953.00 |
| 101 | Café | L1 - Block 35 | 642.97 |
| 103 | Outdoor Covered Dining | L1 - Block 35 | 674.58 |
| 104 | Pocket Park | L1 - Block 35 | 1775.82 |
| 105 | Commercial/Retail | L1 - Block 37 | 1484.79 |
| 108 | Commercial/Retail | L1 - Block 43 | 2303.43 |
| 109 | Commercial/Retail | L1 - Block 43 | 1132.63 |
| 200 | Mezzanine Dining | L2 | 848.55 |

Not homes: three Office Units (301, 401, 501), corridors, stairs, elevators, and the parking level.

## The 20 perspective cameras

Exterior (4):

- Camera fr Above (Realistic) wo Point Cloud. This is the aerial.
- Camera - Exterior Street View (Real)
- Camera - Exterior Street View (Hidden)
- Camera - Exterior River View

Rooftop (3):

- Rooftop Seating Looking toward bandstand
- Green Roof - By Stair 1
- Camera - Fifth Floor Roof Garden

Inside homes (7):

- Loft Unit
- Spiral Stair Loft. Unusable: the camera sits inside a duct.
- Unit 302 - Toward Windows
- Unit 302 - Toward Interior
- Camera - Unit 304 - Toward Core
- Camera at Kitchen 01
- Camera at Kitchen 03

Other interiors (6):

- Residential Lobby
- At Ramp
- Camera - Commercial Space L3
- Camera - Commercial Space L4
- Camera in Stair 3 - Parking Level
- Walkthrough Lobby Stair

The other 16 3D views are orthographic working views: `{3D}`, 3D Solar Study, 3D (Shaded) Uncropped, three stair cutaways, seven "Coord - Arch" views, and three "WV_3D" views.

## Things to fix on the copies

- Coloured ducts from the linked HVAC, plumbing, and electrical models show through the windows in the aerial and street cameras. Hide the links in the copied views.
- The "Unit 302" cameras do not match the room list, where 302 is the L3 corridor. Check which room each interior camera stands in before a photo gets a home number.
- Homes carry number, type, area, and level. They have no "faces river / faces street" value, so the page leaves that out.

Previews of 12 cameras are in `previews/`. They were exported by `export_previews.py`.
