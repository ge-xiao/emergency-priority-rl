import numpy as np
import pandas as pd
import os
import configparser
from environment.judge_ev_env_old import judge_ev_TrafficSimulator
from agents.ma2c import Ma2cAgent
from agents.judge_ev_agent import Judege_ev_agent

class Judege_ev_Trainer():
    def __init__(self, env,judge_run):
        self.env=env
        self.global_step=0
        self.mode="evaluate"
        self.epochs=400
        self.n_step=5
        #多智能体

        self.judge_agents={ts: Judege_ev_agent(n_actions=env.nodes[ts].n_judge_a, n_features=env.judge_n_s_mp[ts], agent_name=ts) for
                                 ts in env.sorted_nodes}
        for ts in env.sorted_nodes:
            path = '../result_judge/output/{}/{}_{}/judge.pt'.format(ts, "train_judge", judge_run)
            self.judge_agents[ts].loadModel(path)

        #self.judge_agents = {ts: Judege_ev_agent(n_actions=env.nodes[ts].n_judge_a, n_features=env.judge_n_s_mp[ts], agent_name=ts) for ts in env.sorted_nodes}
        #test={ts:env.nodes[ts].n_judge_a for ts in env.sorted_nodes}
        #print(test)

    def run(self):
        for i in range(10000, 100001, 10000):
            #print("aaaa")

            initial_states = self.env.reset(mode="evaluate",epoch=i)

            self.mode="evaluate"
            for ts in env.sorted_nodes:
                self.judge_agents[ts].reset()

            print(initial_states)
            state=initial_states
            done=False
            while True:
                #经过n_step训练一次
                actions={}
                for ts in state.keys():
                    s=state[ts]
                    actions[ts]={ ev:self.judge_agents[ts].act(s[ev]) for ev in s.keys()}
                    self.judge_agents[ts].add_transition(s,actions[ts])

                state, reward, done, info=env.step(action=actions)
                # print("state")
                # print(state)

                #更新每个状态动作的奖励
                self.env.get_reward()
                if done:
                    self.env.terminate()
                    self.env.save_judge_result("evaluate", i)
                    print("epoch+"+str(i))
                    break


if __name__ == '__main__':

    config = configparser.ConfigParser()
    #config.read('../config/test_5x5/judge.ini')
    #config.read('../config/test_5x5_2/judge.ini')
    config.read('../config/hangzhou/judge.ini')
    #config.read('../config/manhattan/judge.ini')

    env=judge_ev_TrafficSimulator(config['ENV_CONFIG'],config['MODEL_CONFIG'])

    #model=Ma2cAgent(config['MODEL_CONFIG'],env.n_a_ls,env.n_s_ls,env.sorted_nodes)

    trainer=Judege_ev_Trainer(env,175)
    trainer.run()
