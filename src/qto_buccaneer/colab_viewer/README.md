# IFC Viewer - Interactive 3D Visualization for Google Colab

Modul `colab_viewer` oferă vizualizare interactivă completă pentru modele IFC în Jupyter Notebooks și Google Colab.

## Caracteristici Principale

### 🎨 Vizualizare 3D Interactivă
- Vizualizare 3D cu Plotly (rotire, zoom, pan)
- Culori configurabile prin fișier YAML
- Highlight pentru elemente selectate

### 📊 Tabel Interactiv cu QTO Properties
- Tabel automat cu toate elementele IFC
- Afișare proprietăți QTO (cantități):
  - `Qto_WallBaseQuantities`
  - `Qto_SlabBaseQuantities`
  - `Qto_WindowBaseQuantities`
  - `Qto_DoorBaseQuantities`
  - etc.
- Click pe rând pentru selectare în 3D

### 🔍 Filtre și Control Vizibilitate
- **Filtre Dropdown**:
  - Filter by Storey (nivel/etaj)
  - Filter by IFC Type (IfcWall, IfcSlab, etc.)
- **Control Ierarhic**:
  - Acordeoane pe 3 niveluri: Storey → IFC Type → Element
  - Checkbox individual pentru fiecare element
  - "Select All" pentru fiecare tip
  - "Expand all" / "Collapse all" buttons

### 📝 Panel Proprietăți
- Afișare completă a proprietăților pentru elementul selectat
- Include PropertySets din IFC
- Include QTO properties
- Pentru pereți, include și proprietăți IfcCovering

## Utilizare Simplă

```python
from qto_buccaneer import visualize_ifc

# Vizualizare din URL
url = "https://example.com/model.ifc"
visualize_ifc(url)

# Vizualizare fișier local
visualize_ifc("path/to/model.ifc")

# Cu configurare culori personalizată
visualize_ifc(
    "path/to/model.ifc",
    color_config_path="path/to/colors.yaml",
    verbose=True
)

# Doar 3D, fără UI
viz, hierarchy = visualize_ifc(
    "path/to/model.ifc",
    show_ui=False
)
```

## Parametri

### `visualize_ifc()`

- **`ifc_source`** (str, required): Path sau URL către fișierul IFC
- **`color_config_path`** (str, optional): Path către fișier YAML cu configurare culori
- **`show_ui`** (bool, default=True): Afișează UI complet sau doar 3D
- **`verbose`** (bool, default=False): Afișează informații detaliate despre procesare

## Fișier Configurare Culori (YAML)

```yaml
plots:
  exterior_view:
    elements:
      - name: "Walls"
        filter: "type=IfcWall"
        color: "black"
      - name: "Slabs"
        filter: "type=IfcSlab"
        color: "#808080"
      - name: "Windows"
        filter: "type=IfcWindow"
        color: "#0000FF"
      - name: "Doors"
        filter: "type=IfcDoor"
        color: "#8B4513"
```

## Structura Modulelor

```
colab_viewer/
├── __init__.py                  # Export principal
├── ifc_viewer.py                # Entry point - funcția visualize_ifc()
├── ifc_viewer_loader.py         # Download și load IFC files
├── ifc_viewer_geometry.py       # Extragere geometrie și QTO
├── ifc_viewer_hierarchy.py      # Structură ierarhică (Storey→Type→Element)
├── ifc_viewer_visualizer.py     # Vizualizare 3D cu Plotly
└── ifc_viewer_ui.py             # UI interactiv (NEW!)
```

## Dependințe

```
ifcopenshell
plotly
ipywidgets
scipy
numpy
pyyaml
```

## Instalare în Google Colab

```python
!pip install git+https://github.com/simondilhas/qto_buccaneer.git@main
!pip install ifcopenshell plotly ipywidgets scipy pyyaml

# Activare widgets
from google.colab import output
output.enable_custom_widget_manager()
```

## Workflow Tipic

1. **Instalare**: Rulează celulele de instalare (prima dată)
2. **Import**: `from qto_buccaneer import visualize_ifc`
3. **Vizualizare**: `visualize_ifc(url_or_path)`
4. **Interacțiune**:
   - Folosește filtrele pentru a reduce numărul de elemente afișate
   - Click în tabel pentru a selecta elemente
   - Toggle checkbox-uri pentru show/hide
   - Explorează proprietățile în panel

## Exemple

Vezi notebook-ul complet: `Google Colab notebook/IFC_Viewer_Example.ipynb`

## Note Tehnice

### Extragere Geometrie
- Folosește `Pset_CustomGeometry` cu proprietatea `Custom_Mesh`
- Format JSON cu mesh data (vertices, indices, colors)
- Transform coordinates: swap Y/Z axes

### Extragere QTO
- Caută toate `IfcElementQuantity` sets
- Extrage: Length, Area, Volume, Count, Weight
- Pentru pereți, include și QTO din IfcCovering asociate

### Culori
- Prioritate 1: Culori din fișier YAML config
- Prioritate 2: Culori din Custom_Mesh JSON
- Highlight: Galben (#ffff00) pentru elementele selectate

## Limitări

- Funcționează doar cu modele IFC care conțin `Pset_CustomGeometry`
- UI necesită ipywidgets (Google Colab sau Jupyter Notebook)
- Pentru modele mari (>1000 elemente), poate fi lent

## Dezvoltare Viitoare

- [ ] Support pentru filtre multiple simultane
- [ ] Export selecție la Excel
- [ ] Măsurători în 3D
- [ ] Secțiuni și planuri de secțiune
- [ ] Support pentru clash detection
