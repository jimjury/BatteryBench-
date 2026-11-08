# CellScope Lab｜电池 AI 研究工作台

**定位：融合“公开数据源 + 规范化实验 + 模型结构可视化 + 结果审计”的原创开源项目。**

这不是 BatteryBench / BatteryLife 的简单合并或换皮。它借鉴两者的任务和流程思想，用独立代码实现 SOC、SOH、RUL 的最小闭环，并增加可交互、可解释的静态科研网站。

> 当前为 **v0.1 可运行原型**。项目附带的示例数据由脚本合成，示例测试指标确实由 Python 训练生成，但**不是公开数据集上的论文复现实验**，不能用于宣称模型达到论文精度。

## 功能清单

| 模块 | 已实现 |
|---|---|
| 数据资源中心 | 12 个数据来源/导入协议条目，支持检索、分类和详情弹窗；不镜像第三方原始数据 |
| 预处理实验室 | 交互式抽样/窗口/归一化信号模拟；Python 清洗、去重、相位筛选、无插值抽样、缺口检查 |
| 训练/验证/测试划分 | 电池级分组、固定种子、成员清单、交叉集合重叠审计；SOC 允许循环级对照 |
| 模型动态剧场 | Mean、Ridge、MLP、CNN、GRU、BiLSTM、Transformer、RDB-Attn-BiLSTM 的逐层数据流、形状及说明 |
| 真实训练后端 | 8 个同名可训练模型；两种轻量基线和 6 种可选 PyTorch 模型 |
| 实验配置 | 浏览器导出 JSON，可直接通过 Python CLI 运行 |
| 结果分析 | 读取本项目 `metrics.json`，比较训练/验证/测试 RMSE、MAE 和电池级误差 |
| 科研审计 | 数据哈希、分组成员、只使用训练集拟合归一化、模型选权重来源及限制说明 |

## 安装及运行

```bash
python -m pip install -e .
python -m cellscope demo --out examples/generated/synthetic.csv
python -m cellscope train --config configs/soc_demo.json --out runs/soc_demo
python -m cellscope train --config configs/soh_demo.json --out runs/soh_demo
python -m cellscope train --config configs/rul_demo.json --out runs/rul_demo
```

使用深度网络需要单独安装：

```bash
python -m pip install -e '.[neural]'
```

修改 `configs/soc_demo.json` 中的 `"model": "ridge"` 为 `"model": "rdb_attn_bilstm"` 等即可训练；如使用真实数据，还需修改 `data.path`、真实标签及其来源。网页也可以直接导出这一格式的配置。

## 打开 HTML 网页

解压后直接双击 `web/index.html`；或在项目根目录执行 `python -m http.server 8000`，访问 `http://localhost:8000/web/`。静态网站不要求后台服务，可作为 GitHub Pages 网站部署。

**重要区别：** 网页里的模型动画是结构演示，不是真实训练权重的激活可视化；信号实验室是浏览器端确定性模拟，不会修改 CSV；只有 Python 后端执行实际训练。网页版可以导入本地实验生成的 `metrics.json` 查看结果。

## 数据与评估协议

基本字段：`cell_id, cycle_index, time_s, voltage_v, current_a, temperature_c`。再提供一个任务标签：`soc`、`soh` 或 `rul_cycles`。支持把常见 `Voltage_V, Current_A, T, SOC` 等别名规范化。

**SOC**：默认窗口 64，每个样本使用第 1–64 个观测点的电压、电流、温度，预测第 65 个点的 SOC。滑动步长 1；不允许跨电池、跨循环或超时缺口。模型结构与研究者已有 SOC 主线兼容，但本仓库默认是独立通用 benchmark，而不是移植其已有代码。

**SOH / RUL**：从每循环观测提取五项与容量标签无直接重叠的时序统计特征；用当前及之前窗口内循环汇总预测当前循环标签。SOH 的容量标准及 RUL 的 EOL 定义取决于数据来源，必须自行确认；程序不会把最后记录自动当作 EOL。

**归一化**：支持训练集拟合 Min-Max、Z-Score 与关闭归一化，验证/测试共享同一训练统计量。默认按电池划分，训练和测试电池互不重叠。实验输出有严格的原始文件 SHA256、分组成员、参数和预测结果。

完整技术细节见 [DATA_PROTOCOL](docs/DATA_PROTOCOL.md)、[ARCHITECTURE](docs/ARCHITECTURE.md)。

## 质量验证

```bash
python -m pip install -e '.[test,neural]'
python -m pytest -q
node --test tests-js/*.cjs
python scripts/verify_assets.py
```

浏览器自动化需要 Chromium 和 Playwright；当前测试环境的 Chromium 被管理策略禁止访问任何 URL，因此浏览器级自动点击**未能完成**，并不宣称已通过该项。请查看 [QA 状态](docs/QA.md)。Python/Node 的自动化测试已通过。

## 与参考开源项目的关系

- [BatteryBench](https://github.com/LMDHQ-0420/BatteryBench)：参考多模型、多任务的统一实验协议。
- [BatteryLife](https://github.com/Ruifeng-Tan/BatteryLife)：参考数据标准化和寿命预测任务组织方式。
- [BatteryML](https://github.com/microsoft/BatteryML)、[BEEP](https://github.com/TRI-AMDD/beep)、[PyBaMM](https://github.com/pybamm-team/PyBaMM)：参考生态和未来扩展方向。

本仓库未复制上述项目源码，未打包第三方数据，具体来源与引用详见 [REFERENCES](docs/REFERENCES.md)。
