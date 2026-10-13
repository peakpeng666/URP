"""Reuse the frozen independent assignment/L1 checker without modifying it."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from paper_baseline_v1.src.checker import check_assignment,aggregate_records
