import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.metrics import calculate_all_metrics
from qto_buccaneer.utils.config import load_config
from qto_buccaneer.utils.ifc_loader import IfcLoader

config = load_config("src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml")
filepath = "examples/Mustermodell V1_abstractBIM_sp_enriched.ifc"

loader = IfcLoader(filepath)
file_info = {
    "file_name": Path(loader.file_path).name,
    "file_schema": loader.model.schema,
}

all_metrics = calculate_all_metrics(config, filepath, file_info)
print(all_metrics)

#save to excel
all_metrics.to_excel("examples/all_metrics.xlsx", index=False)

#all_metrics = calculate_all_metrics("metrics_config_abstractBIM.yaml", "your_ifc_file.ifc")