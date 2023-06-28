import gym
import numpy as np
import pandas as pd
import os
import configparser
from environment.EMVLight_env import TrafficSimulator
from agents.EMVLight_ma2c import Ma2cAgent
from train import Trainer

# from agents.ma2c import Ma2cValueNet
# from agents.ma2c import Ma2cPolicyNet


class Evaluate(Trainer):
    def __init__(self, env, model,num_ev=-1):
        super().__init__(env, model)
        self.name="evaluate"
        self.mode="evaluate"
        self.num_ev=num_ev
        self.evaluate_seed=range(10000, 100001, 10000)

    def test(self,train_run):
        self.loadModel(train_run)

        for seed in self.evaluate_seed:
            if self.num_ev>0:
                ob = self.env.reset(mode="evaluate", epoch=seed,evaluate_seed=seed,num_ev=self.num_ev)
            else:
                ob = self.env.reset(mode="evaluate", epoch=seed,evaluate_seed=seed)


            self.model.resetLstm()

            while True:
                ob,v,done,c_reward=self.expore(ob)

                if done:
                    self.env.terminate()
                    if self.num_ev > 0:
                        self.env.saveResult("evaluate_" + str(self.num_ev), seed)
                    else:
                        self.env.saveResult("evaluate", seed)
                    print("seed+"+str(seed))
                    break


    def loadModel(self,run):
        policyPath=[]
        valuePath=[]
        for node_name in self.model.sorted_nodes:
            path = '../result/output/{}/{}_{}/'.format(node_name, 'train', run)
            policyPath.append(path+'policy.pt')
            valuePath.append(path+'value.pt')
        self.model.loadModel(policyPath,valuePath)



if __name__ == '__main__':

    config = configparser.ConfigParser()
    #config.read('../config/test_5x5/EMVLight.ini')
    #config.read('../config/test_5x5_2/EMVLight.ini')
    #config.read('../config/hangzhou/EMVLight.ini')
    #config.read('../config/manhattan/EMVLight.ini')

    env = TrafficSimulator(config['ENV_CONFIG'],mode="evaluate")
    #env.hasPrune=True
    model = Ma2cAgent(config['MODEL_CONFIG'], env.n_a_ls, env.n_s_ls, env.sorted_nodes)
    eva=Evaluate(env,model)
    #eva=Evaluate(env,model,1)

    eva.test(200)



