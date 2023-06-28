import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt
import copy
import os


class OnPolicyBuffer():
    def __init__(self,n_features,memory_size=500, batch_size=32):
        self.evs=[]
        self.states={}
        self.actions={}
        self.rewards={}

        self.memory_size = memory_size
        self.batch_size = batch_size
        # initialize zero memory [s, a, r, s_]
        self.memory = np.zeros((self.memory_size, n_features * 2 + 2))
        self.memory_counter = 0


    def reset(self):

        self.evs=[]
        self.states={}
        self.actions={}
        self.rewards={}

    def add_transition(self,ev, state,action):
        self.evs.append(ev)
        self.states[ev]=state
        self.actions[ev]=action

    def updateReward(self,ev,reward):
        # print("updatereward")
        # print(ev)
        # print(reward)

        self.rewards[ev]=reward
        s=self.states[ev]
        a=self.actions[ev]
        r=reward
        ev_idx=self.evs.index(ev)
        ev_next_idx=(ev_idx+1)%len(self.evs)
        s_=self.states[self.evs[ev_next_idx]]
        transition = np.hstack((s, [a, r], s_))
        # replace the old memory with new memory
        index = self.memory_counter % self.memory_size
        self.memory[index, :] = transition
        self.memory_counter += 1



    def sample_transition(self):
        #print("sample_transition")
        #print(self.memory_counter)

        # sample batch memory from all memory
        if self.memory_counter > self.memory_size:
            sample_index = np.random.choice(self.memory_size, size=self.batch_size)
        else:
            sample_index = np.random.choice(self.memory_counter, size=min(self.memory_counter,self.batch_size))

        batch_memory = self.memory[sample_index, :]
        #print(batch_memory)
        return batch_memory



class Net(nn.Module):
    def __init__(self, n_feature, n_hidden, n_output):
        super(Net, self).__init__()
        self.el = nn.Linear(n_feature, n_hidden)
        self.q = nn.Linear(n_hidden, n_output)

    def forward(self, x):
        x = self.el(x)
        x = F.relu(x)
        x = self.q(x)
        return x



class Judege_ev_agent():
    def __init__(self,n_actions, n_features,agent_name, n_hidden=20, learning_rate=0.01, reward_decay=0.9, e_greedy=0.9,batch_size=32,replace_target_iter=200,e_greedy_increment=None):
        self.agent_name=agent_name
        self.batch_size=batch_size
        self.trans_buffer=OnPolicyBuffer(n_features=n_features,batch_size=batch_size)
        self.n_actions = n_actions
        self.n_features = n_features
        self.n_hidden = n_hidden
        self.lr = learning_rate
        self.gamma = reward_decay
        self.epsilon_max = e_greedy
        self.replace_target_iter = replace_target_iter
        self.epsilon_increment = e_greedy_increment
        self.epsilon = 0 if e_greedy_increment is not None else self.epsilon_max

        # total learning step
        self.learn_step_counter = 0
        self.loss_func = nn.MSELoss()
        self.cost_his = []
        self._build_net()


    def _build_net(self):
        self.q_eval = Net(self.n_features, self.n_hidden, self.n_actions)
        self.q_target = Net(self.n_features, self.n_hidden, self.n_actions)
        self.optimizer = torch.optim.RMSprop(self.q_eval.parameters(), lr=self.lr)


    def act(self,observation):
        observation = torch.tensor(observation, dtype=torch.float)
        observation = observation.view(1, -1)
        if np.random.uniform() < self.epsilon:
            actions_value = self.q_eval(observation)

            action = np.argmax(actions_value.data.numpy())
        else:
            action = np.random.randint(0, self.n_actions)
        #self.action = random.randint(0,15)
        return action


    def learn(self):
        #边界条件
        if self.trans_buffer.memory_counter==0:
            return


        # check to replace target parameters
        if self.learn_step_counter % self.replace_target_iter == 0:
            self.q_target.load_state_dict(self.q_eval.state_dict())
            # print("\ntarget params replaced\n")

        batch_memory=self.trans_buffer.sample_transition()

        # q_next is used for getting which action would be choosed by target network in state s_(t+1)
        q_next, q_eval = self.q_target(torch.Tensor(batch_memory[:, -self.n_features:])), self.q_eval(
            torch.Tensor(batch_memory[:, :self.n_features]))
        # used for calculating y, we need to copy for q_eval because this operation could keep the Q_value that has not been selected unchanged,
        # so when we do q_target - q_eval, these Q_value become zero and wouldn't affect the calculation of the loss
        q_target = torch.Tensor(q_eval.data.numpy().copy())

        batch_index = np.arange(len(batch_memory), dtype=np.int32)
        eval_act_index = batch_memory[:, self.n_features].astype(int)
        reward = torch.Tensor(batch_memory[:, self.n_features + 1])
        q_target[batch_index, eval_act_index] = reward + self.gamma * torch.max(q_next, 1)[0]

        loss = self.loss_func(q_eval, q_target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # increase epsilon
        self.cost_his.append(loss)
        self.epsilon = self.epsilon + self.epsilon_increment if self.epsilon < self.epsilon_max else self.epsilon_max
        self.learn_step_counter += 1


    def add_transition(self,state,action):
        for ev in state.keys():
            self.trans_buffer.add_transition(ev,state[ev],action[ev])

    def updateReward(self,reward):
        for ev in reward.keys():
            self.trans_buffer.updateReward(ev,reward[ev])
        #print(self.trans_buffer.rewards)

    def reset(self):
        self.trans_buffer.reset()

    def saveModel(self, name, run):
        net = self.q_eval
        path = '../result_judge/output/{}/{}_{}/'.format(self.agent_name, name, run)
        if not os.path.exists(path):
            os.makedirs(path)

        torch.save(net, path + 'judge.pt')

    def loadModel(self,judgePath):

        self.q_eval=torch.load(judgePath)


