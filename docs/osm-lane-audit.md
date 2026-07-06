# Corridor data audit — OSM tagging, signals, counts, travel times

Generated 2026-07-06 by `python/scripts/audit_osm_lanes.py`
from data fetched by `fetch_corridor_osm.py` and
`fetch_toronto_open_data.py`. Regenerate by rerunning those scripts.
Evidence base for ADR-0007 (network format) and `docs/validation.md`.

## OSM extract overview

- Drive network, bbox `(-79.475, 43.65, -79.395, 43.745)` (west, south, east, north)
- 3,885 nodes, 10,542 directed edges after simplification
- Signalized nodes (`highway=traffic_signals`): 448

### Way tag coverage (the lane-inference workload)

| Edge set | Edges | `lanes` | `turn:lanes*` | `maxspeed` |
|---|---|---|---|---|
| All edges | 10542 | 98% | 9% | 61% |
| Major roads (motorway..tertiary) | 3019 | 98% | 29% | 76% |
| Corridor-named streets | 878 | 100% | 30% | 63% |

### Corridor streets, individually

| Street match | Edges | `lanes` | `turn:lanes*` | `maxspeed` |
|---|---|---|---|---|
| Eglinton | 179 | 100% | 40% | 53% |
| Allen | 28 | 100% | 39% | 64% |
| St Clair | 99 | 100% | 38% | 25% |
| Bathurst | 229 | 100% | 17% | 72% |
| Dufferin | 203 | 100% | 25% | 55% |
| Bloor | 140 | 100% | 41% | 100% |

### Turn-restriction relations (Overpass, not in the osmnx graph)

- 753 relations in bbox: `<untagged>` x411, `no_left_turn` x161, `no_u_turn` x76, `no_right_turn` x50, `no_straight_on` x24, `only_right_turn` x20, `only_straight_on` x5, `only_left_turn` x3, `no_right_turn_on_red` x2, `no_left_turn @ Mo-Fr 07:00-09:00` x1

## Corridor traffic signals (Toronto Open Data: Traffic Signals Tabular)

- 167 signals in-bbox on corridor-named streets
- System / control-mode distribution: `TransSuite/SAP` x53, `TransSuite/SA2` x45, `TransSuite/SA1` x44, `TransSuite/FT` x12, `TransSuite/PA - MPS` x6, `TransSuite/SAV` x5, `TransSuite/PA - IPS` x2

### Key corridor junctions

| PX | Junction | System | Control mode | Transit preempt |
|---|---|---|---|---|
| 0100 | BATHURST ST / EGLINTON AVE W | TransSuite | SA1 | - |
| 0105 | DUFFERIN ST / EGLINTON AVE W | TransSuite | FT | - |
| 0321 | BLOOR ST W / BATHURST ST | TransSuite | FT | 1 |
| 0325 | DUFFERIN ST / BLOOR ST W | TransSuite | SA1 | 1 |
| 0480 | ST CLAIR AVE W / BATHURST ST | TransSuite | SA1 | 1 |
| 0488 | DUFFERIN ST / ST CLAIR AVE W | TransSuite | SA1 | 1 |
| 0772 | EGLINTON AVE W / WILLIAM R ALLEN RD S | TransSuite | SA1 | - |
| 1063 | DUFFERIN ST / DUFFERIN PARK AVE | TransSuite | SAP | 1 |
| 1307 | EGLINTON AVE W / WILLIAM R ALLEN RD N | TransSuite | SAV | - |
| 1347 | YORKDALE 401 ALLEN N RAMP / ALLEN X N 401 C E RAMP | TransSuite | SA2 | - |

## Control-mode legend (from the dataset's readme)

- The Traffic Signal dataset contains information about the City of Toronto's electronic traffic control devices composed of traffic signals, pedestrian crossovers and flashing beacons.
- Most of the traffic signal lights are centrally controlled by one of the following Traffic Signal Control Systems: MTSS, SCOOT/UTC, TransSuite or Aries.  Sometimes a signal is "Awaiting" a system control as the communication infrastructure has not been completed. Rarely, a signal is "Local" or "temporary", meaning that there are no immediate plans connect the signal to a central system.
- A traffic signal light operates with a particular mode of control as follows:
- SAV = Semi-actuated with presence loops.  Vehicle extensions, no push buttons or “Walk” display.
- SA2 = Semi-actuated with presence loops and push buttons.  Vehicles and pedestrians can receive different times.  There are vehicle extensions, and push button activation is required for “Walk” display.
- SIGNAL_SYSTEM   -  MTSS, SCOOT, TransSuite, Aries, or Awaiting TransSuite
- MODE_OF_CONTROL   -  FXT, SAP, SAP on Recall, SAV, SA2, PED
- SIGNAL_SYSTEM   -  MTSS, SCOOT, TransSuite, Aries, or Awaiting TransSuite
- MODE_OF_CONTROL   -  FXT, SAP, SAP on Recall, SAV, SA2, PED

## Corridor turning movement counts (most recent per intersection)

- 314 counted corridor locations in-bbox
- Latest-count year distribution: 2026: 41, 2025: 70, 2024: 48, 2023: 25, 2022: 17, 2021: 11, 2020: 4, 2019: 7, 2018: 4, 2017: 7, 2016: 14, 2015: 7, 2014: 6, 2013: 2, 2012: 6, 2011: 3, 2010: 4, 2009: 1, 2008: 3, 2007: 1, 2006: 7, 2005: 6, 2004: 4, 2003: 2, 2002: 1, 2001: 1, 1999: 1, 1996: 1, 1994: 3, 1993: 2, 1991: 2, 1989: 1, 1985: 1, 1984: 1

### Key corridor junctions

| Location | Latest count | Duration (h) | Total vehicles |
|---|---|---|---|
| Dufferin St / Jane Osler Blvd / Yorkdale Dufferin N Ramp | 1994-07-21 | 8R | 6045 |
| Bathurst St / Lane S of Dundas and W of Bathurst | 1994-11-17 | 8S | 10017 |
| Eglinton Ave W / Lascelles Blvd / Eglinton Park Trl | 2010-07-27 | 8R | 14011 |
| Allen Express S Lawrence Ramp / Allen Rd | 2011-07-07 | 8R | 20091 |
| Dufferin St / Hwy 401 Collectors E Dufferin St S Ramp | 2016-03-22 | 8R | 23906 |
| Dufferin St / Dufferin Grove Park Trl (id: 30057152) | 2016-04-28 | 8R | 10922 |
| Lawrence Ave W: Lawrence Allen Express N Ramp - Lawrence W / Allen Express S Ramp | 2020-02-29 | 8R | 18987 |
| Allen Express S Lawrence Ramp / Lawrence Ave W / Lawrence W Allen Express S Ramp | 2022-11-15 | 8R | 16914 |
| Allen Express N Lawrence Ramp / Lawrence Allen Express N Ramp / Lawrence Ave W | 2022-11-15 | 8R | 19032 |
| Salem Ave / Lane N of Bloor and W of Westmoreland / Lane N of Bloor and E of Bartlett | 2023-01-18 | 8R | 677 |
| Bartlett Ave / Lane N of Bloor and E of Bartlett / Lane/1 /2of Bloor and W of Bartlett | 2023-01-18 | 8R | 700 |
| Allen N Yorkdale Rd Ramp / Hwy 401 Allen N Ramp / Yorkdale / Yorkdale Rd | 2023-10-24 | 14 | 14280 |
| Allen N Yorkdale Rd Ramp / Hwy 401 Allen N Ramp / Yorkdale | 2024-05-29 | 14 | 12194 |
| Dufferin St / Sylvan Ave / Dufferin Grove Park Trl | 2024-09-05 | 14 | 15843 |
| Allen Rd / Transit Rd / William R Allen Rd / Wilson Hs S Allen Rd Ramp | 2024-10-24 | 14 | 60961 |
| Dufferin St / Briar Hill Ave / Dufferin Hill Park Trl | 2024-11-26 | 14 | 24152 |
| Dufferin St / Dufferin Park Ave / Dufferin Grove Park Trl | 2025-09-20 | 14 | 17971 |
| Dufferin St / Bloor St W | 2025-09-20 | 14 | 25287 |
| Bathurst St / St Clair Ave W | 2025-10-18 | 14 | 35540 |
| Dufferin St / St Clair Ave W | 2025-10-18 | 14 | 24501 |
| Dufferin St / Eglinton Ave W | 2026-01-14 | 14 | 35207 |
| Allen Rd / Eglinton Ave W (West) | 2026-03-24 | 14 | 31663 |
| Bathurst St / Eglinton Ave W | 2026-03-24 | 14 | 43966 |
| Allen Rd / Eglinton Ave W (East) | 2026-03-24 | 14 | 39906 |
| Eglinton Ave E / Yonge St / Eglinton Ave W | 2026-03-24 | 14 | 23902 |
| Bathurst St / Bloor St W | 2026-05-13 | 14 | 24206 |

## Bluetooth travel-time route coverage (2014-2017 program)

- 60 routes citywide; 14 intersect the corridor bbox
- Route attributes available: resultId, normalDriv, length_m, geometry
- Corridor-intersecting routes: AC1_AC2, AC1_AD3, AC2_AC1, AC2_AC3, AC2_AQ2, AC3_AC2, AD1_AD2, AD2_AD1, AD2_AD3, AD3_AC1, AD3_AD2, AD3_AD4, AD4_AD3, AQ2_AC2

