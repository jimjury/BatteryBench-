import json
import pytest
from pathlib import Path
from cellscope.synthetic import generate_demo
from cellscope.pipeline import run_experiment
from cellscope.models import create_neural_model


def config(path, task, window):
    return {'task': task,'model':'ridge',
            'data':{'path':str(path),'phase':'discharge','discharge_sign':'negative','max_gap_sec':2,'synthetic':True},
            'features':{'window':window},
            'split':{'unit':'battery','seed':42,'val_fraction':.2,'test_fraction':.2},
            'train':{'alpha':1.0}}


@pytest.mark.parametrize('task,window', [('soc',6),('soh',3),('rul',3)])
def test_end_to_end_json_and_metrics(tmp_path,task,window):
    source=tmp_path/'synthetic.csv';generate_demo(source,cells=5,cycles=9,points=12)
    out=tmp_path/f'run_{task}'
    result=run_experiment(config(source,task,window),output_dir=out)
    loaded=json.loads((out/'metrics.json').read_text())
    assert result['task']==task
    assert loaded['audit']['train_only_scaler']
    assert loaded['audit']['group_overlap'] is False
    assert loaded['selection']['uses_test_for_model_selection'] is False
    assert loaded['features']['sequence_label_alignment']==('next_time_step' if task=='soc' else 'current_cycle')
    assert loaded['metrics']['test']['rmse']>=0
    assert loaded['metrics']['test']['n']>0
    assert len(list(out.glob('predictions_*.csv')))==3
    assert len(loaded['source']['sha256'])==64


def test_refuse_health_cycle_split(tmp_path):
    source=tmp_path/'synthetic.csv';generate_demo(source,cells=5,cycles=9,points=12)
    cfg=config(source,'rul',3);cfg['split']['unit']='cycle'
    with pytest.raises(ValueError,match='battery-level'):
        run_experiment(cfg,output_dir=tmp_path/'run')


def test_every_neural_model_accepts_tensor():
    torch=pytest.importorskip('torch')
    for name in ['mlp','cnn','gru','bilstm','transformer','rdb_attn_bilstm']:
        net=create_neural_model(name,8,3,hidden=16)
        with torch.no_grad():
            result=net(torch.randn(2,8,3))
        assert result.shape==(2,),name
        assert torch.isfinite(result).all(),name
