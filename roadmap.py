"""
JANUS roadmap — engines from the product vision that don't have a real
engines/<name>.py module yet. app.py shows these as "Roadmap" in the sidebar.

Once you build one for real: create engines/<name>.py with an ENGINE dict +
render() function (see any existing engine for the pattern), and DELETE its
entry from this list. app.py auto-discovers the new module and will show it
as Active — no other edits needed anywhere.
"""

ROADMAP_ENGINES = [
    {"name": "UKPE", "full_name": "Universal Knowledge Processing Engine", "icon": "📄",
     "desc": "Summaries, notes, flashcards, and mind maps from large document sets.",
     "order": 5},
    {"name": "AMIE", "full_name": "Medical Intelligence Engine", "icon": "🩺",
     "desc": "Digital twin, 3D anatomy, disease and medicine intelligence.",
     "order": 6},
    {"name": "NAVIS", "full_name": "Navigation Intelligence", "icon": "🗺️",
     "desc": "Route planning and geographic reasoning via A*/Dijkstra.",
     "order": 7},
    {"name": "USE", "full_name": "Universal Simulation Engine", "icon": "🧪",
     "desc": "Interactive simulation across physics, chemistry, engineering, medicine.",
     "order": 8},
    {"name": "UDI", "full_name": "Universal Design Intelligence", "icon": "🏗️",
     "desc": "Idea → requirements → 3D model → simulation → engineering report.",
     "order": 9},
]
