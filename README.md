# emergency-priority-rl

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repo implements TLLight: A Two-layer Reinforcement Learning Approach based Intelligent Traffic Signal Control System for EV Priority in SUMO-simulated environments.


## Requirements
* Python3==3.8
* [Pytorch](https://pytorch.org/)==1.8
* [SUMO](http://sumo.dlr.de/wiki/Installing)>=1.14.0

## Usages
All the experiment settings are in a config file under `[config]`. All the nets are included under `[net]`. To conduct experiments, you need to enter the `[experience]` folder.

1. To train the collaboration decision layer
~~~
python3 judge_ev_train.py
~~~
data will be output to `[base_dir]/result_judge`

2. To evaluate the trained collaboration decision layer
~~~
python3 judge_ev_evaluate.py
~~~
Evaluation data will be output to `[base_dir]/result_judge`


3. To train the agent with two layer
~~~
python3 combine_train.py
~~~
data will be output to `[base_dir]/result`

4. To evaluate the trained agent with two layer
~~~
python3 combine_train.py
~~~
Evaluation data will be output to `[base_dir]/result`

5. To measure the agent behavior, run
~~~
python3 result.plot.py
~~~



