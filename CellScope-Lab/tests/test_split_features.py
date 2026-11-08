import numpy as np
import pandas as pd
import pytest
from cellscope.split import make_splits
from cellscope.features import build_samples, Standardizer
from cellscope.evaluate import scores, low_soc
from cellscope.synthetic import generate_demo
from cellscope.data import load_csv


def test_battery_split_reproducible_and_disjoint():
    df = pd.DataFrame({'cell_id': [f'c{i}' for i in range(8)], 'cycle_index':[1]*8})
    a,meta=make_splits(df,seed=42,val_fraction=.125,test_fraction=.25)
    b,meta2=make_splits(df,seed=42,val_fraction=.125,test_fraction=.25)
    assert meta==meta2
    assert meta['disjoint']
    assert {str(x) for x in a['train'].cell_id}.isdisjoint(set(a['test'].cell_id))
    assert all(len(a[k])>0 for k in a)


def test_soc_next_step_no_cross_gap_and_label():
    rows=[]
    for cell in ['a','b','c']:
        for t in [0,1,2,10,11,12]:
            rows.append((cell,1,t,t+1,-1,25,t/12))
    f = pd.DataFrame(rows,columns=['cell_id','cycle_index','time_s','voltage_v','current_a','temperature_c','soc'])
    batch=build_samples(f,task='soc',window=2,max_gap_sec=2)
    assert len(batch.y)==6 # two gap-separated segments per cell
    assert np.allclose(batch.y[:2],[2/12,1])
    assert batch.x.shape==(6,2,3)
    assert np.allclose(batch.x[0,:,0],[1,2])


def test_health_windows_and_label_integrity(tmp_path):
    path=tmp_path/'demo.csv';generate_demo(path,cells=4,cycles=8,points=9)
    df=load_csv(path,task='soh').frame
    samples=build_samples(df,task='soh',window=4)
    assert samples.x.shape==(4*5,4,5)
    assert len(samples.y)==20
    broken=df.copy()
    broken.loc[0,'soh']=.2
    with pytest.raises(ValueError,match='constant within each cycle'):
        build_samples(broken,task='soh',window=4)


def test_train_only_standardization():
    train=np.ones((3,2,2),dtype=np.float32)
    val=np.full((1,2,2),4,dtype=np.float32)
    z=Standardizer().fit(train)
    assert z.as_dict()['fit_on']=='training_only'
    assert np.allclose(z.transform(train),0)
    assert np.allclose(z.transform(val),3)


def test_metric_no_zero_division_and_empty():
    s=scores(np.array([0.,1.,2.]),np.array([.1,1.1,1.9]))
    assert s['mape_eligible']==2
    assert s['rmse']>0
    assert low_soc(np.array([.8,.3]),np.array([.9,.4]))['metrics'] is None
    assert scores(np.array([]),np.array([])) is None
