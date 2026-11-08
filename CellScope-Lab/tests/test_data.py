import numpy as np
import pandas as pd
import pytest
from cellscope.data import canonical_columns, load_csv
from cellscope.synthetic import generate_demo


def test_alias_support_and_ambiguity():
    df = pd.DataFrame({"Voltage_V": [4.0], "Current_A": [-1.0], "T": [25]})
    assert list(canonical_columns(df)) == ["voltage_v", "current_a", "temperature_c"]
    with pytest.raises(ValueError, match="Ambiguous"):
        canonical_columns(pd.DataFrame({"Voltage_V": [4.0], "voltage_v": [4.0]}))


def test_robust_ingestion_and_row_decimation(tmp_path):
    source = tmp_path / "raw.csv"
    pd.DataFrame([
        ['A',1,0,3.9,-1,25,.95],['A',1,1,3.8,-1,25,.9],
        ['A',1,1,3.7,-1,25,.8], # duplicate timestamp
        ['A',1,2,3.6,0,25,.8],  # rest phase
        ['A',1,3,3.5,-1,25,.75],
        ['A',1,4,'error',-1,25,.7], # invalid numeric row
        ['A',1,5,3.4,-1,25,.6]
    ], columns=['cell_id','Cycle','Time','Voltage','Current','T','SOC']).to_csv(source,index=False)
    ing = load_csv(source,decimation_step=2,max_gap_sec=2)
    assert ing.report['input_rows'] == 7
    assert ing.report['invalid_rows'] == 1
    assert ing.report['duplicate_timestamps'] == 1
    assert ing.report['phase_filtered_rows'] == 1
    assert ing.report['output_rows'] == 2
    assert ing.report['interpolated_rows'] == 0
    assert list(ing.frame.time_s)==[0,3]
    assert ing.report['gaps_above_limit']==1


def test_invalid_labels_and_phase(tmp_path):
    p = tmp_path / 'd.csv'
    generate_demo(p,cells=3,cycles=4,points=8)
    frame=pd.read_csv(p)
    frame.loc[0,'soc']=95
    frame.to_csv(p,index=False)
    with pytest.raises(ValueError, match='SOC label'):
        load_csv(p)
    with pytest.raises(ValueError, match='No samples remain'):
        load_csv(p,phase='discharge',discharge_sign='positive',task='soh')
