/* Architecture diagrams follow actual Python model variants in cellscope/models.py. */
(function (root) {
  const designs = [
    {id:'rdb_attn_bilstm', name:'RDB · Attention · BiLSTM', short:'Hybrid', family:'HYBRID', desc:'自研示例：Pointwise 投影 → 残差深度可分离卷积（BN + ReLU）→ 单层双向 LSTM → 单头注意力 → MLP。逐层采用真实后端的维度变化。', tags:['Residual Depthwise','BiLSTM × 1','Single-head Attention','Regressor'], stages:(w,f)=>[
      ['输入时序',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'同一循环内按时间排序的输入；SOC 三特征 V/I/T。','每个时间点包含全部特征，窗口末端标签不属于输入。'],
      ['1×1 投影',`B × ${w} × ${f}`,`B × ${w} × 48`,'Pointwise Conv1d 把输入通道映射到 48 维表示。','不会改变时间长度。'],
      ['残差深度卷积',`B × ${w} × 48`,`B × ${w} × 48`,'Depthwise k=3 + Pointwise + BatchNorm + shortcut + ReLU。','残差路径保持通道维度与长度，便于保留局部信息。'],
      ['BiLSTM × 1',`B × ${w} × 48`,`B × ${w} × 96`,'一次双向循环编码；前向与反向各 48 维拼接。','仅在已观察的窗口内双向建模，不使用预测目标时刻的未来输入。'],
      ['单头 Attention',`B × ${w} × 96`,'B × 96','单层线性打分、softmax 时间权重、加权求和。','这里显示概念流程，并非训练模型导出的注意力值。'],
      ['MLP 输出','B × 96','B × 1','48 维 ReLU 隐层投影到一个连续目标。','输出未强制裁剪：是否施加物理边界应由任务协议决定。']
    ]},
    {id:'transformer', name:'Transformer Encoder', short:'Transformer', family:'ATTENTION', desc:'将时序特征映射到隐空间并叠加位置编码，经一层 TransformerEncoder 提取全局依赖，平均池化后回归。', tags:['Projection','Positional Encoding','1 Encoder','Mean Pool'], stages:(w,f)=>[
      ['输入时序',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'有限长度的历史序列。','无目标时刻输入。'],
      ['线性投影 + 位置编码',`B × ${w} × ${f}`,`B × ${w} × 48`,'将通道投影并加入正弦位置编码。','动态位置表示不是从数据直接读取的标签。'],
      ['Transformer Encoder',`B × ${w} × 48`,`B × ${w} × 48`,'4 头自注意力与前馈网络组成单个编码器层。','注意力作用域仅是输入窗口。'],
      ['均值池化',`B × ${w} × 48`,'B × 48','沿时间轴平均聚合。','与选择最后一个时间点的隐状态不同。'],
      ['线性预测','B × 48','B × 1','回归目标标量。','回归头与任务共享接口。']
    ]},
    {id:'bilstm', name:'Bidirectional LSTM', short:'BiLSTM', family:'RECURRENT', desc:'一个双向 LSTM 编码观测窗口，以最后一个双向隐向量回归目标。', tags:['Recurrent','Bidirectional','1 Layer'], stages:(w,f)=>[
      ['输入时序',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'固定历史窗口。','不跨越周期。'],['双向 LSTM',`B × ${w} × ${f}`,`B × ${w} × 96`,'正反两个方向提取窗口内的时序结构。','只能使用窗口内的信息。'],['末端状态','B × '+w+' × 96','B × 96','取编码后的最后一个时间步。','该实现使用 output[:, -1, :]。'],['线性回归','B × 96','B × 1','输出任务标签。','适合公平基线。']
    ]},
    {id:'gru', name:'GRU Sequence', short:'GRU', family:'RECURRENT', desc:'单层 GRU 的门控序列建模，更少参数的轻量时序基线。',tags:['Gated RNN','1 Layer','Last State'],stages:(w,f)=>[
      ['输入',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'原始序列被训练集统计量标准化。','分组隔离在模型外完成。'],['GRU 编码',`B × ${w} × ${f}`,`B × ${w} × 48`,'重置门与更新门控制时间信息流。','单向编码。'],['末端状态',`B × ${w} × 48`,'B × 48','取最后时间点表征。','保持样本顺序。'],['线性预测','B × 48','B × 1','输出连续目标。','可以与 BiLSTM 做参数与性能对照。']
    ]},
    {id:'cnn', name:'Temporal CNN', short:'CNN', family:'CONVOLUTION', desc:'一维卷积局部捕捉电压、电流和温度的联动变化，经自适应平均池化后预测。',tags:['Conv1D k=3','ReLU','Global Average Pool'],stages:(w,f)=>[
      ['输入',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'时序传感器输入。','先换轴以适配 Conv1d。'],['通道转置',`B × ${w} × ${f}`,`B × ${f} × ${w}`,'将特征放在 Conv1D 通道维。','张量中的物理时间顺序未变化。'],['1D 卷积',`B × ${f} × ${w}`,`B × 48 × ${w}`,'48 个 k=3 的卷积核提取局部模式并 ReLU。','padding=1 保持长度。'],['平均池化',`B × 48 × ${w}`,'B × 48','将整个窗口压缩成一个表征。','保留通道数量。'],['线性输出','B × 48','B × 1','连续回归结果。','标准卷积基线。']
    ]},
    {id:'mlp', name:'Flatten MLP', short:'MLP', family:'DENSE', desc:'将整个输入窗口展开，经一个 ReLU 全连接隐藏层输出回归值；对模型深度与非线性贡献提供基线。', tags:['Flatten','Dense 48','ReLU'], stages:(w,f)=>[
      ['输入',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'固定形状窗口。','先标准化。'],['展平',`B × ${w} × ${f}`,`B × ${w*f}`,'按时间和通道顺序展平。','失去显式的二维时序结构。'],['Dense + ReLU',`B × ${w*f}`,'B × 48','一个可学习隐藏层。','动态非线性回归。'],['线性输出','B × 48','B × 1','回归目标值。','适合与更复杂模型对照。']
    ]},
    {id:'ridge', name:'Ridge Regression', short:'Ridge', family:'STATISTICAL', desc:'将窗口直接展平，采用不惩罚截距的岭回归，提供结构清晰、可快速复现的定量基线。',tags:['Linear','SVD','L2 Regularization'],stages:(w,f)=>[
      ['输入',`B × ${w} × ${f}`,`B × ${w} × ${f}`,'经过训练集均值/方差标准化的时序窗口。','只拟合训练集合。'],['展平',`B × ${w} × ${f}`,`B × ${w*f}`,'将序列按固定次序展开。','固定模型输入维度。'],['Ridge / SVD',`B × ${w*f}`,'B × 1','利用训练集 SVD 求解带 L2 正则的系数。','截距不正则化，超参数 alpha 默认 1。'],['预测','B × 1','B × 1','使用拟合的系数对测试窗口线性预测。','没有经过训练的深度层。']
    ]},
    {id:'mean', name:'Mean Label Baseline', short:'Mean', family:'NULL BASELINE', desc:'训练时计算训练集标签均值；测试预测为常数，完全不依赖输入。可检验复杂模型是否真的优于无信息基线。', tags:['Constant','Train-only Label Mean','Sanity Check'], stages:(w,f)=>[
      ['训练标签',`N train × 1`,'N train × 1','仅用于学习常数。','不使用验证或测试标签。'],['训练集均值','N train × 1','1','计算训练集标签均值。','忽略全部输入特征。'],['常数预测','1','B × 1','对所有样本返回相同的训练集均值。','必须作为对照而非神经网络。']
    ]}
  ];
  const map = Object.fromEntries(designs.map(d => [d.id,d]));
  root.CellModels = {designs,map,stages:(id,w,task='soc')=>map[id].stages(w,task==='soc'?3:5)};
})(window);
