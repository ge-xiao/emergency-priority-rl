import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import gym
import numpy as np
import pandas as pd
import os
import configparser
from environment.new_env import TrafficSimulator
from agents.ma2c import Ma2cAgent
from agents.judge_ev_agent import Judege_ev_agent

import torch.nn.utils.prune as prune

from torch.optim.lr_scheduler import StepLR

class Combine_trainer():
    def __init__(self,env,model):
        self.env=env
        self.model=model
        self.n_step=model.n_step
        self.epochs=model.epochs
        self.global_step=0
        self.mode="train"
        self.train_reward=[]
        self.test_reward=[]
        self.train_interact_time=[]
        self.test_interact_time=[]
        self.tot_hasev_ls=[]



    def expore(self,prev_ob):
        ob=prev_ob
        done=False
        rewards=[]

        for _ in range(self.n_step):

            value = self.model.value_net_forward(ob)
            policy = self.model.policy_net_forward(ob)

            self.env.update_fingerprint(policy)

            action=[]

            EPSILON=1
            #for pi in policy:
            for i in range(len(policy)):
                pi=policy[i]
                n_a=self.model.n_a_ls[i]
                if np.random.uniform() < EPSILON:  # ϵ-greedy 策略对动作进行采取

                    a = np.random.choice(np.arange(len(pi)), p=pi)
                else:
                    a = np.random.randint(n_a)
                action.append(a)


            next_ob, reward, done, global_reward = self.env.step(action)
            rewards.append(global_reward)
            #print(reward)
            self.model.add_transition(ob, action, reward, value, done)

            ob = next_ob

            if done:
                break

        v = self.model.value_net_forward(ob)
        return ob,v,done,rewards


    def save_global_reward(self,rewards,i):
        output_path = '../result/output/global_reward/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        rewards = np.array(rewards)
        mean_reward = np.mean(rewards)
        std_reward = np.std(rewards)
        log = {
            'epoch': i,
            'avg_reward': mean_reward,
            'std_reward': std_reward}
        if self.mode=="train":
            self.train_reward.append(log)
            df = pd.DataFrame(self.train_reward)
            df.to_csv(output_path + ('%s_%s_global_reward.csv' % ('train', i)), index=False)
        else:
            self.test_reward.append(log)
            df = pd.DataFrame(self.test_reward)
            df.to_csv(output_path + ('%s_%s_global_reward.csv' % ('test', i)), index=False)


    def run(self):

        for i in range(self.epochs):
            ob = self.env.reset(mode="combine_train",epoch=i)
            self.model.resetLstm()
            self.mode="train"

            rewards=[]
            while True:
                ob,v,done,c_reward=self.expore(ob)
                rewards+=c_reward
                self.model.learn(v)
                #计算node cover率
                #self.env.get_reward()
                if done:
                    self.env.terminate()
                    self.model.saveModel("train",i)
                    self.env.saveResult("train",i)
                    print("epoch+"+str(i))
                    self.save_global_reward(rewards,i)
                    break


            # if i>0 and i%10==0:
            #     ob = self.env.reset(mode="combine_test",epoch=i)
            #     self.model.resetLstm()
            #     self.mode = "test"
            #     rewards = []
            #
            #     while True:
            #         ob, v, done,c_reward = self.expore(ob)
            #         rewards += c_reward
            #         if done:
            #             self.env.terminate()
            #             self.env.saveResult("test",i)
            #             print("test+" + str(i))
            #             self.save_global_reward(rewards, i)
            #             break



if __name__ == '__main__':

    config = configparser.ConfigParser()
    #config.read('../config/test_5x5/judge.ini')
    #config.read('../config/test_5x5_2/judge.ini')
    #config.read('../config/hangzhou/judge.ini')
    #config.read('../config/manhattan/judge.ini')

    env=TrafficSimulator(config['ENV_CONFIG'],mode="combine_train")
    model=Ma2cAgent(config['MODEL_CONFIG'],env.n_a_ls,env.n_s_ls,env.sorted_nodes)

    trainer=Combine_trainer(env,model)
    trainer.run()
