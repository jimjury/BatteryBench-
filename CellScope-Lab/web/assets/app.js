(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const catalog = window.CELLSCOPE_CATALOG || [];
  const demoReport = window.CELLSCOPE_DEMO_RUN;
  const Core = window.CellCore;
  const Designs = window.CellModels;
  const colors = () => {
    const css = getComputedStyle(document.body);
    return Object.fromEntries(['mint','blue','muted','faint','outline','text','bg'].map(k => [k, css.getPropertyValue(`--${k}`).trim()]));
  };
  const on = (id, event, fn) => { const el = $(id); if (el) el.addEventListener(event, fn); };
  const setText = (id, text) => { if ($(id)) $(id).textContent = String(text); };
  const make = (tag, text, cls) => { const el = document.createElement(tag); if (text != null) el.textContent = String(text); if (cls) el.className = cls; return el; };
  const number = val => Number(val).toLocaleString('en-US');
  const signalState = {step:1,window:64,norm:'raw'};
  let datasetFilter = 'all', selectedModel = 'rdb_attn_bilstm', layerIndex = 0;
  let animation = null, currentReport = demoReport;

  function initNavigation() {
    on('nav-toggle','click',() => {
      const opened = $('sidebar').classList.toggle('open');
      $('nav-toggle').setAttribute('aria-expanded', String(opened));
    });
    document.querySelectorAll('.nav-link').forEach(a => a.addEventListener('click',() => {
      $('sidebar').classList.remove('open');
      $('nav-toggle').setAttribute('aria-expanded','false');
    }));
    on('theme-toggle','click',() => {
      document.body.classList.toggle('light');
      updateSignal(); renderResults(currentReport);
    });
    const navLinks = Array.from(document.querySelectorAll('.nav-link'));
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => {
        const first = entries.filter(v=>v.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
        if (!first) return;
        navLinks.forEach(n=>n.classList.toggle('active',n.dataset.section===first.target.id));
        setText('breadcrumb', first.target.dataset.title || '研究总览');
      }, {rootMargin:'-10% 0px -62% 0px',threshold:0});
      document.querySelectorAll('.section').forEach(x=>observer.observe(x));
    }
  }

  function initCatalog() {
    setText('overview-datasets',String(catalog.length).padStart(2,'0'));
    setText('overview-models',String(Designs.designs.length).padStart(2,'0'));
    document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
      datasetFilter = button.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(el => el.classList.toggle('selected',el===button));
      renderCatalog();
    }));
    on('dataset-search','input',renderCatalog);
    on('modal-close','click',closeModal);
    on('dataset-modal','click',event=>{if(event.target===$('dataset-modal'))closeModal();});
    document.addEventListener('keydown',event=>{if(event.key==='Escape')closeModal();});
    renderCatalog();
  }
  function renderCatalog() {
    const query = $('dataset-search').value.trim().toLowerCase();
    const items = catalog.filter(d => (datasetFilter==='all'||d.type===datasetFilter) &&
      [d.name,d.chemistry,d.type,...d.focus,d.notes].join(' ').toLowerCase().includes(query));
    const parent = $('dataset-grid');parent.replaceChildren();
    items.forEach((d) => {
      const button = make('button',null,'dataset-card');
      button.type='button';button.setAttribute('aria-label',`查看 ${d.name} 数据来源详情`);
      const top = make('div',null,'dataset-card-top');
      const types = {'aging':'AGING / LIFE','multi-ion':'MULTI-ION','soc':'IMPORT PROTOCOL'};
      top.append(make('span',types[d.type]||'DATA SOURCE','type-token'),make('span',d.id.toUpperCase(),'dataset-num'));
      button.append(top,make('h3',d.name),make('p',d.chemistry));
      const tags=make('div',null,'dataset-tags'); d.focus.forEach(t=>tags.append(make('span',t)));
      button.append(tags,make('span','↗','dataset-arrow'));
      button.addEventListener('click',()=>showDataset(d));parent.append(button);
    });
    setText('dataset-count',`当前显示 ${items.length} / ${catalog.length} 项公开来源与导入协议。`);
  }
  let previousFocus=null;
  function showDataset(d) {
    previousFocus=document.activeElement;
    setText('modal-title',d.name);
    const dl=make('dl',null,'modal-list');
    const entries=[['类型',d.type==='soc'?'本地导入协议':'外部数据源'],['电池体系',d.chemistry],['适用研究任务',d.focus.join(' / ')],['数据格式',d.format],['覆盖内容',d.coverage],['来源引用',d.citation],['访问方式',d.access],['许可说明',d.license],['研究备注',d.notes]];
    for(const [key,value] of entries){dl.append(make('dt',key),make('dd',value));}
    const dt=make('dt','源站链接'),dd=make('dd');const link=make('a','打开原始来源 ↗');
    if (typeof d.source==='string'&&d.source.startsWith('https://')) {
      link.href=d.source;link.target='_blank';link.rel='noopener noreferrer';dd.append(link);
    } else dd.textContent='未核实链接';
    dl.append(dt,dd);$('modal-body').replaceChildren(dl);
    $('dataset-modal').classList.remove('hidden');$('modal-close').focus();
  }
  function closeModal(){if(!$('dataset-modal').classList.contains('hidden')){$('dataset-modal').classList.add('hidden');if(previousFocus&&previousFocus.focus)previousFocus.focus();}}

  function canvasSetup(id,height) {
    const canvas=$(id),rect=canvas.getBoundingClientRect();
    const width=Math.max(260,rect.width||600);
    const dpr=Math.min(2,window.devicePixelRatio||1);
    canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
    const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
    return {ctx,width,height};
  }
  function drawLines(id, series, height=230) {
    const {ctx,width}=canvasSetup(id,height), c=colors(), left=32,right=13,top=12,bottom=25;
    ctx.clearRect(0,0,width,height);
    ctx.font='10px sans-serif';ctx.textAlign='right';ctx.lineWidth=1;
    ctx.strokeStyle=c.outline;ctx.fillStyle=c.faint;
    for(let i=0;i<5;i++){const y=top+(height-top-bottom)*i/4;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(width-right,y);ctx.stroke();ctx.fillText(String(Math.round((1-i/4)*100))+'%',left-7,y+3);}
    const normalized=series.map(s=>{
      const vals=s.data.map(t=>t.v), min=Math.min(...vals), max=Math.max(...vals);return {...s, data:s.data.map(p=>({x:p.x,v:(p.v-min)/(max-min||1)}))};
    });
    const allX=series.flatMap(s=>s.data.map(p=>p.x)); const minX=Math.min(...allX),maxX=Math.max(...allX);
    for(let i=0;i<5;i++){const x=left+(width-left-right)*i/4;ctx.textAlign='center';ctx.fillText(String(Math.round(minX+(maxX-minX)*i/4)),x,height-7);}
    for(const s of normalized){
      ctx.beginPath(); ctx.strokeStyle=s.color; ctx.lineWidth=s.width||2;ctx.globalAlpha=s.alpha||1;
      if(s.dashed)ctx.setLineDash([5,5]);else ctx.setLineDash([]);
      s.data.forEach((p,i)=>{const x=left+(p.x-minX)/(maxX-minX||1)*(width-left-right),y=top+(1-p.v)*(height-top-bottom);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});ctx.stroke();
    }ctx.globalAlpha=1;ctx.setLineDash([]);
  }
  function initPipeline(){
    ['pipe-step','pipe-window','pipe-norm'].forEach(id=>on(id,id==='pipe-norm'?'change':'input',()=>{
      signalState.step=Number($('pipe-step').value);
      signalState.window=Number($('pipe-window').value);
      signalState.norm=$('pipe-norm').value;
      updateSignal();
    }));
    updateSignal();
  }
  function updateSignal(){
    const d=Core.prepareSignal(signalState);
    setText('pipe-step-value',signalState.step);setText('pipe-window-value',signalState.window);
    setText('pipe-in',number(d.raw.length));setText('pipe-out',number(d.count));
    setText('pipe-windows',number(d.windows));setText('pipe-shape',d.shape);
    setText('pipe-scale-summary',`训练拟合样本：${d.trainingFitCount} 行 · 输出数值范围：${d.outputRange[0].toFixed(3)} ~ ${d.outputRange[1].toFixed(3)} (${signalState.norm})`);
    const c=colors();
    drawLines('signal-chart',[
      {data:d.raw.map(r=>({x:r.index,v:r.v})),color:c.faint,alpha:.55,width:1.5,dashed:true},
      {data:d.processed.map(r=>({x:r.index,v:r.plotted})),color:c.mint,width:2.5}
    ]);
  }

  function initSplits(){
    ['split-unit','split-seed','split-test'].forEach(id=>on(id,'input',updateSplit));
    updateSplit();
  }
  function updateSplit(){
    const unit=$('split-unit').value,seed=Math.max(0,Math.floor(Number($('split-seed').value)||0)),frac=Number($('split-test').value)/100;
    const d=Core.splitDemo(seed,frac,unit);
    setText('split-seed-value',seed);setText('split-test-value',`${Math.round(frac*1000)/10}%`);
    const parent=$('split-grid');parent.replaceChildren();
    d.tiles.forEach(cell=>{
      const tile=make('div',null,'split-cell'), label=make('span',cell.id),bars=make('div',null,'split-cell-bars');
      cell.parts.forEach(group=>{const bar=make('i',null,group);bar.title=group;bars.append(bar);});tile.append(label,bars);parent.append(tile);
    });
    const summary=$('split-summary');summary.replaceChildren();
    ['train','val','test'].forEach(k=>{const el=make('div');el.append(make('b',d.counts[k]),make('span',`${k.toUpperCase()} GROUPS`));summary.append(el);});
    const note=$('split-note');note.classList.toggle('warning',d.overlap);
    note.textContent=d.overlap?'⚠ 同一电池出现在多个集合：循环级划分不适用于跨电池泛化结论。':'✓ 分组互斥：每块电池只属于一个集合，适合跨电池评估。';
    if(unit==='cycle'&&!d.overlap)note.textContent='注意：即使随机分配偶然未重叠，循环级划分仍不是独立电池评估。';
  }

  function stopModelAnimation(){if(animation!==null){clearInterval(animation);animation=null;}setText('model-play','▶ 播放路径');}
  function initModels(){
    const tabs=$('model-tabs'),select=$('exp-model');
    Designs.designs.forEach(d=>{
      const btn=make('button',d.short,'model-tab');btn.type='button';btn.dataset.model=d.id;
      btn.setAttribute('aria-pressed','false');btn.addEventListener('click',()=>renderModel(d.id,0));tabs.append(btn);
      const op=make('option',d.name);op.value=d.id;select.append(op);
    });
    on('model-play','click',()=>{
      if(animation!==null){stopModelAnimation();return;}
      setText('model-play','Ⅱ 暂停');
      advanceModel();
      const ms=()=>Math.max(250,1350/Number($('model-speed').value));
      animation=setInterval(advanceModel,ms());
    });
    on('model-speed','change',()=>{if(animation!==null){stopModelAnimation();$('model-play').click();}});
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stopModelAnimation();});
    renderModel(selectedModel,0);
  }
  function renderModel(id,index=0){
    stopModelAnimation();selectedModel=id;layerIndex=index;
    const d=Designs.map[id];
    document.querySelectorAll('.model-tab').forEach(el=>{const active=el.dataset.model===id;el.classList.toggle('selected',active);el.setAttribute('aria-pressed',String(active));});
    setText('model-title',d.name);setText('model-about-name',d.name);setText('model-about-text',d.desc);
    const tags=$('model-tags');tags.replaceChildren();d.tags.forEach(t=>tags.append(make('span',t)));
    const flow=$('model-flow');flow.replaceChildren();
    const stages=Designs.stages(id,signalState.window,'soc');
    stages.forEach((layer,i)=>{
      const el=make('button',null,'flow-step');el.type='button';el.dataset.index=i;
      const initials=['⬡','⟁','⌁','◎','◈','∑','↗'];
      el.append(make('span',initials[i%initials.length],'flow-icon'),make('strong',layer[0]),make('small',layer[2]));
      el.addEventListener('click',()=>selectLayer(i));flow.append(el);
      if(i<stages.length-1)flow.append(make('span','→','flow-arrow'));
    });
    selectLayer(index);
  }
  function selectLayer(index){
    const d=Designs.map[selectedModel],stages=Designs.stages(selectedModel,signalState.window,'soc');
    layerIndex=Math.min(index,stages.length-1);const [name,input,output,desc,note]=stages[layerIndex];
    flowSelect(layerIndex);
    setText('inspector-number',`LAYER ${String(layerIndex+1).padStart(2,'0')} / ${stages.length}`);
    setText('inspector-name',name);setText('inspector-desc',desc);
    setText('inspector-in',input);setText('inspector-out',output);setText('inspector-note',note);
    setText('model-progress-label',`${String(layerIndex+1).padStart(2,'0')} / ${String(stages.length).padStart(2,'0')}`);
    $('model-progress').style.width=`${(layerIndex+1)/stages.length*100}%`;
  }
  function flowSelect(index){document.querySelectorAll('.flow-step').forEach(el=>{const active=Number(el.dataset.index)===index;el.classList.toggle('selected',active);el.setAttribute('aria-pressed',String(active));if(active)el.scrollIntoView({block:'nearest',inline:'nearest',behavior:'smooth'});});}
  function advanceModel(){const size=Designs.stages(selectedModel,signalState.window,'soc').length;selectLayer((layerIndex+1)%size);}

  function currentExperiment(){
    return Core.experimentConfig({task:$('exp-task').value,model:$('exp-model').value,
      window:Number($('exp-window').value),normalization:$('exp-norm').value,seed:Number($('exp-seed').value),
      splitUnit:$('exp-split').value,testFraction:Number($('exp-test').value)});
  }
  function initExperiments(){
    $('exp-model').value=selectedModel;
    ['exp-task','exp-model','exp-window','exp-norm','exp-seed','exp-split','exp-test'].forEach(id=>{
      on(id,'input',()=>{
        if(id==='exp-task'){
          const health=$('exp-task').value!=='soc';
          $('exp-split').value='battery';$('exp-split').querySelector('option[value="cycle"]').disabled=health;
          $('exp-window').value=health?'6':'64';
        }
        updateExperiment();
      });
    });
    on('exp-download','click',()=>{
      try {
        const config=currentExperiment(),body=JSON.stringify(config,null,2),blob=new Blob([body],{type:'application/json'}),url=URL.createObjectURL(blob);
        const a=make('a');a.href=url;a.download=`cellscope_${config.task}_${config.model}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
        setText('exp-status','已生成可供本地 CLI 使用的 JSON 配置。');
      }catch(e){setText('exp-status',e.message);}
    });
    on('exp-copy','click',async()=>{
      try {
        const body=JSON.stringify(currentExperiment(),null,2);
        if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(body);}
        else{const tmp=make('textarea');tmp.value=body;tmp.style.position='fixed';tmp.style.opacity='0';document.body.append(tmp);tmp.select();if(!document.execCommand('copy'))throw Error('当前浏览器不支持剪贴板复制');tmp.remove();}
        setText('exp-status','已复制配置 JSON。');
      }catch(e){setText('exp-status',`复制失败：${e.message}，可使用下载配置按钮。`);}
    });
    updateExperiment();
  }
  function updateExperiment(){
    try {
      const cfg=currentExperiment();setText('exp-preview',JSON.stringify(cfg,null,2));
      setText('exp-command',`python -m cellscope train --config experiment.json --out runs/${cfg.task}_${cfg.model}`);
      $('exp-download').disabled=false;$('exp-copy').disabled=false;
      setText('exp-status','校验通过。配置引用 data/your_dataset.csv，请替换成真实 CSV 路径。');
    }catch(e){setText('exp-preview',`配置无效：${e.message}`);setText('exp-status',e.message);$('exp-download').disabled=true;$('exp-copy').disabled=true;}
  }

  function initResults(){
    on('result-upload','change',async e=>{
      const file=e.target.files?.[0];if(!file)return;
      try{
        if(file.size>5*1024*1024)throw Error('JSON 文件超过 5 MB');
        const report=JSON.parse(await file.text());
        if(!Core.validReport(report))throw Error('不是有效的 CellScope metrics.json v1.0');
        currentReport=report;renderResults(report);setText('results-warning',`已读取本地文件：${file.name}。数据只在本机浏览器中处理。`);
      }catch(err){setText('results-warning',`导入失败：${err.message}`);}
      e.target.value='';
    });
    on('result-reset','click',()=>{currentReport=demoReport;renderResults(demoReport);setText('results-warning','已恢复项目随附的合成数据 CLI 运行报告。');});
    renderResults(demoReport);
  }
  function renderResults(report){
    if(!Core.validReport(report)){setText('results-warning','当前无法读取结果，请确认 metrics.json 完整且符合项目结构。');return;}
    currentReport=report;
    const m=report.metrics, synthetic=report.source?.synthetic;
    setText('result-source',`${synthetic?'● SYNTHETIC DEMO':'● IMPORTED EXPERIMENT'} · ${report.model.toUpperCase()} · ${report.task.toUpperCase()}`);
    setText('result-tag',synthetic?'SYNTHETIC TEST RUN':'IMPORTED REPORT');
    const kpis=$('result-kpis');kpis.replaceChildren();
    const stats=[['TEST RMSE',Core.pretty(m.test.rmse),'Lower is better'],['TEST MAE',Core.pretty(m.test.mae),'Lower is better'],['TEST SAMPLES',number(m.test.n),'Out-of-group evaluation'],['TASK / MODEL',report.task.toUpperCase(),report.model]];
    stats.forEach(([label,value,sub])=>{const el=make('div',null,'result-kpi');el.append(make('span',label),make('b',value),make('small',sub));kpis.append(el);});
    const meta=$('result-provenance');meta.replaceChildren();
    const entries=[['TASK',report.task.toUpperCase()],['MODEL',report.model],['WINDOW',report.features.window],['SPLIT UNIT',report.split.unit],['TRAIN UNITS',report.split.counts.train],['TEST UNITS',report.split.counts.test],['SOURCE SHA256',String(report.source?.sha256||'not supplied').slice(0,18)+'…']];
    for(const [key,val] of entries)meta.append(make('dt',key),make('dd',val));
    const audit=report.audit||{};
    setText('result-audit',`组间重叠：${audit.group_overlap===false?'无':'未确认'} · Train-only fit：${audit.train_only_scaler===true?'是':'未确认'} · Test 参与选权重：${report.selection?.uses_test_for_model_selection===false?'否':'未确认'}`);
    const tbody=$('cell-metrics-body');tbody.replaceChildren();
    const cellData=report.by_cell.test||{};
    Object.keys(cellData).sort().forEach(cell=>{
      const s=cellData[cell];if(!s)return;
      const tr=make('tr');[cell,s.n,Core.pretty(s.rmse),Core.pretty(s.mae)].forEach(v=>tr.append(make('td',v)));tbody.append(tr);
    });
    if(!Object.keys(cellData).length){const tr=make('tr'),cell=make('td','当前报告无电池级明细');cell.colSpan=4;tr.append(cell);tbody.append(tr);}
    drawBars(report);
    setText('results-warning',synthetic?'此结果仅来自项目生成的合成数据，不能与 BatteryBench / BatteryLife 实验排名直接比较。':'已导入外部结果；请独立核验数据源、划分规则、标签口径和运行环境。');
  }
  function drawBars(report){
    const {ctx,width,height}=canvasSetup('result-chart',240),c=colors(),names=['train','val','test'],heightChart=155;
    ctx.clearRect(0,0,width,height);ctx.font='11px sans-serif';
    const metrics=names.flatMap(k=>[report.metrics[k].rmse,report.metrics[k].mae]);
    const scale=Math.max(...metrics)*1.18||1, left=44,right=12,top=20;
    ctx.lineWidth=1;
    for(let i=0;i<=4;i++){const y=top+heightChart*(1-i/4);ctx.strokeStyle=c.outline;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(width-right,y);ctx.stroke();ctx.fillStyle=c.faint;ctx.textAlign='right';ctx.fillText(Core.pretty(scale*i/4,3),left-8,y+3);}
    const groupWidth=(width-left-right)/3,barWidth=Math.max(13,Math.min(28,groupWidth/4));
    names.forEach((name,index)=>{
      const center=left+groupWidth*(index+.5),a=report.metrics[name];
      [[a.rmse,c.mint,-1],[a.mae,c.blue,1]].forEach(([v,color,sign])=>{
        const bh=v/scale*heightChart,x=center+(sign===-1?-barWidth-3:3),y=top+heightChart-bh;
        ctx.fillStyle=color;ctx.fillRect(x,y,barWidth,bh);
      });
      ctx.fillStyle=c.muted;ctx.textAlign='center';ctx.fillText(name.toUpperCase(),center,top+heightChart+20);
    });
    ctx.fillStyle=c.mint;ctx.fillRect(width-168,height-18,9,9);ctx.fillStyle=c.text;ctx.textAlign='left';ctx.fillText('RMSE',width-155,height-10);
    ctx.fillStyle=c.blue;ctx.fillRect(width-88,height-18,9,9);ctx.fillStyle=c.text;ctx.fillText('MAE',width-75,height-10);
  }

  document.addEventListener('DOMContentLoaded',()=>{
    initNavigation();initCatalog();initPipeline();initSplits();initModels();initExperiments();initResults();
    let nextDraw=null;
    window.addEventListener('resize',()=>{clearTimeout(nextDraw);nextDraw=setTimeout(()=>{updateSignal();renderResults(currentReport);},130);});
  });
})();
