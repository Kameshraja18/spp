# Road Safety Intelligence Dashboard - User Guide

## Dashboard Overview

The dashboard has three audience modes accessible via tabs at the top of the right panel:
- **🚓 Police** - Rapid response and patrol planning
- **🗺️ Dispatch** - Real-time routing and unit coordination
- **📊 Planner** - Infrastructure investment planning

---

## 🚓 Police Tab

### Purpose
Help traffic police and rapid response units decide patrol routes and pre-positioning strategies.

### Features

#### 1. Currently Selected Segment
Shows at the top of the panel:
```
📍 Currently selected: S42 – NH44_Hosur
```
This updates automatically when you click "View →" on any segment in the Top 5 list, or click a marker on the map.

#### 2. Response Actions by Risk Band
Shows guidance for different risk levels:
- **🔴 CRITICAL (0.75+)**: Pre-position units, activate beacons, continuous monitoring
- **🟠 HIGH (0.60–0.74)**: Deploy standard patrol, enable signage, prepare response

#### 3. Incident Severity Predictor
**How to use**:
1. Enter a segment ID (e.g., "S1")
2. Select weather condition (Clear, Rain, Fog, Snow)
3. Select light condition (Daylight, Dusk, Dark)
4. Click "🔴 Predict Severity"

**Output shows**:
- Expected Severity Level (No Injury / Minor / Serious / Fatal)
- Recommended Response (Standard patrol → Full emergency response)
- Probability breakdown for each severity class

**Error Handling**:
- Invalid segment ID format → Error message
- Missing weather selection → Error message
- Missing light condition → Error message

---

## 🗺️ Dispatch Tab

### Purpose
Help dispatch centers coordinate unit response, choose optimal routes, and manage real-time incident routing.

### Features

#### 1. 24-Hour Risk Forecast
**How to use**:
1. Enter a segment ID (e.g., "S1")
2. Click "📊 Generate 24h Forecast"

**Output shows**:
- Hourly risk percentages for next 24 hours
- Peak risk hour detection
- Patrol deployment timing recommendation

#### 2. Real-Time Routing & Unit Positions
When you click "View →" or select a segment, the Dispatch panel shows:
```
Segment Coordinates: 37.7749, -122.4194
Suggested Routes & ETAs:
• Unit A: Route A (Direct) – 8 min (12 km)
• Unit B: Route B (Safe) – 12 min (15 km)  
• Unit C: Route C (Local) – 15 min (14 km)
```

This helps dispatch quickly assign units to specific routes based on current constraints.

---

## 📊 Planner Tab

### Purpose
Help traffic and infrastructure planners identify recurring hotspots and make data-driven investment decisions.

### Features

#### 1. Monthly Hotspot Statistics
When you click "View →" on a segment, the Planner panel shows:
```
Monthly Stats:
Total Incidents: 12
Serious/Fatal: 4/1

Patterns:
• Weekday peak hours
• Rainy conditions
• High speed variance

Infrastructure Actions:
✓ Install median barrier
✓ Upgrade lighting to LED
✓ Add rumble strips
```

#### 2. Export Options

**Option A: Download Full Report**
- File: `hotspot-report-2026-01-06.csv`
- Contains: All segments with monthly risk, incident counts, patterns, and recommended actions
- Use for: Monthly department briefings, board presentations, budget justification

**Option B: Export Last 30 Days**
- File: `history-30days-2026-01-06.csv`
- Contains: Daily incident data for trend analysis
- Use for: Identifying emerging hotspots, measuring enforcement impact

#### 3. Intervention Packages
Pre-built packages for common scenarios:
- **Weather Response Package**: Drainage, LED lighting, markings
- **Work Zone Safety Package**: Rumble strips, barriers, retroreflective sheeting
- **High-Traffic Intersection Package**: Signal timing, pedestrian refuges

---

## How Tabs Work

1. **Click any tab** (Police/Dispatch/Planner)
2. **Right panel switches** to that audience's view
3. **Left panel (map) stays** the same - same risk data, different context
4. **Click "View →"** on any Top 5 segment:
   - Map centers on that segment
   - Marker opens popup
   - Right panel updates with segment-specific details
   - Selection label shows which segment you're acting on

---

## Common Workflows

### Police Officer Workflow
1. Check top 5 hotspots on map
2. Click "View →" on high-risk segment
3. Read "Currently selected" label
4. Check Response Actions guidance
5. Use Severity Predictor if accident occurs
6. Download CSV for briefing

### Dispatch Coordinator Workflow
1. Identify incident location on map
2. Click segment to see coordinates
3. Check Suggested Routes & ETAs
4. Assign Unit A/B/C based on ETA
5. Request 24-hour forecast for planning
6. Monitor peak risk hours

### Infrastructure Planner Workflow
1. Review monthly hotspots on map
2. Click "View →" on recurring hotspot
3. Check total incidents and serious/fatal counts
4. Review suggested Infrastructure Actions
5. Download Full Report for budget justification
6. Export 30-Day History to track trends

---

## Tips & Best Practices

✓ **Map Click**: Directly clicking a map marker shows that segment's details in all three panels

✓ **Validation**: The Severity Predictor validates all inputs before calling the API - fixes like segment format, weather selection, light condition

✓ **ETA Planning**: Dispatch should use the suggested routes to pre-assign units during peak risk hours

✓ **Export Timing**: Run Full Report at month-end, 30-Day History weekly for trend tracking

✓ **Selection Label**: Always check "Currently selected" label to avoid acting on wrong segment

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Severity Predictor shows error | Check segment ID format (alphanumeric), select weather AND light condition |
| Map not centering | Click "View →" button, not the segment ID directly |
| Export file empty | Ensure at least one hotspot is loaded from the monthly report |
| Selection label not showing | Click a segment in Top 5 list or on map first |
| Route ETAs not showing | Must be in Dispatch tab and select a segment |

---

## Safety Notice

⚠️ **All predictions are advisory only** and are NOT replacements for:
- Official road safety assessments
- Current traffic conditions verification
- Engineering feasibility studies
- Local regulations and protocols

Police must verify against real-time conditions. Planners must conduct full studies. All actions must comply with local standards.
