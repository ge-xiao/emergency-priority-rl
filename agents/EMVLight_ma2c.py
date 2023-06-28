import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import gym
import numpy as np
import pandas as pd
import os
import configparser
from environment.env import TrafficSimulator
import torch.nn.utils.prune as prune

from torch.optim.lr_scheduler import StepLR

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')



class OnPolicyBuffer():
    def __init__(self,gamma):
        self.obs = []
        self.acts = []
        self.rs = []
        self.vs = []
        self.gamma=gamma

    def reset(self):
        # the done before each step is required
        self.obs = []
        self.acts = []
        self.rs = []
        self.vs = []

    def add_transition(self, ob, a, r, v, done):

        self.obs.append(ob)
        self.acts.append(a)
        self.rs.append(r)
        self.vs.append(v)

    def sample_transition(self,vb):
        Rs = []
        Advs = []
        R=vb

        # for r, v in zip(self.rs[::-1], self.vs[::-1]):
        #     R = r + self.gamma * R
        #     #Adv = R - v
        #     Adv = v-R
        #     Rs.append(R)
        #     Advs.append(Adv)
        # Rs.reverse()
        # Advs.reverse()

        error=[]
        for i in range(len(self.acts)-1):
            r=self.rs[i]

            #multi step reward
            # target = r
            # right=min(i+10,len(self.acts)-1)
            # for j in range(i+1,right,1):
            #     target+=(self.gamma**(j-i))*self.rs[j]
            # target += (self.gamma**(right-i)) * self.vs[right]

            target=r+self.gamma*self.vs[i+1]
            error.append(self.vs[i]-target)
            Rs.append(target)
        r = self.rs[len(self.acts)-1]
        target = r + self.gamma * vb
        error.append(self.vs[len(self.acts)-1] - target)
        Rs.append(target)
        Advs=error
        #print(Rs)

        obs=self.obs
        acts=self.acts
        self.reset()

        return obs, acts, Rs, Advs



class Ma2cPolicyNet(nn.Module):
    def __init__(self, n_s,n_a):
        super(Ma2cPolicyNet, self).__init__()
        self.hidden_size = 64
        self.num_layers=1
        self.nums_cell=128

        self.h = torch.zeros(self.num_layers, 1, self.hidden_size)
        self.c = torch.zeros(self.num_layers, 1, self.hidden_size)
        self.n_a=n_a

        self.fc1 = nn.Linear(n_s, self.nums_cell)
        self.lstm = nn.LSTM(self.nums_cell, self.hidden_size,batch_first=True)
        self.fc2 = nn.Linear(self.hidden_size, n_a)
        self.relu=nn.ReLU()
        self.tanh=nn.Tanh()

        self.dropout = nn.Dropout(p=0.5)  # dropout训练


    def forward(self, x):
        x=self.fc1(x)
        #x = self.dropout(x)
        x=self.tanh(x)

        x=x.view(1,-1,self.nums_cell)

        # # Forward propagate LSTM
        out, (hn,cn) = self.lstm(x, (self.h, self.c))  # out: tensor of shape (batch_size, seq_length, hidden_size*2)
        self.h,self.c=hn.detach(),cn.detach()
        x=self.fc2(out)
        #x=self.tanh(x)

        x=x.view(-1,self.n_a)
        x = F.softmax(x, dim = -1) # 概率归一化
        return x

    def resetLstm(self):
        self.h = torch.zeros(self.num_layers, 1, self.hidden_size)
        self.c = torch.zeros(self.num_layers, 1, self.hidden_size)


class Ma2cValueNet(nn.Module):
    def __init__(self, n_s):
        super(Ma2cValueNet, self).__init__()
        self.hidden_size = 64
        self.num_layers=1
        self.nums_cell=128


        self.h = torch.zeros(self.num_layers, 1, self.hidden_size)
        self.c = torch.zeros(self.num_layers, 1, self.hidden_size)

        self.fc1 = nn.Linear(n_s, self.nums_cell)

        self.lstm = nn.LSTM(self.nums_cell, self.hidden_size,batch_first=True)
        self.fc2 = nn.Linear(self.hidden_size,1)
        self.relu=nn.ReLU()
        self.tanh=nn.Tanh()

        self.dropout = nn.Dropout(p=0.5)  # dropout训练


    def forward(self, x):

        x=self.fc1(x)
        #x = self.dropout(x)
        x=self.tanh(x)

        x=x.view(1,-1,self.nums_cell)

        # # Forward propagate LSTM
        out, (hn,cn) = self.lstm(x, (self.h, self.c))  # out: tensor of shape (batch_size, seq_length, hidden_size*2)
        self.h,self.c=hn.detach(),cn.detach()

        x=self.fc2(out)
        #x=self.tanh(x)

        x=x.view(-1,1)
        return x

    def resetLstm(self):
        self.h = torch.zeros(self.num_layers, 1, self.hidden_size)
        self.c = torch.zeros(self.num_layers, 1, self.hidden_size)

def init_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.normal_(m.weight, mean=0, std=0.1)

class Ma2cAgent:
    def __init__(self,config,n_a_ls,n_s_ls,sorted_nodes):
        self.n_step=config.getint('n_step')
        self.epochs=config.getint('epochs')
        self.n_a_ls=n_a_ls
        self.n_s_ls=n_s_ls
        #print(n_s_ls)
        self.n_agent=len(n_s_ls)
        self.sorted_nodes=sorted_nodes


        self.trans_buffer_ls = []
        self.gamma = config.getfloat('gamma')

        for i in range(self.n_agent):
            self.trans_buffer_ls.append(OnPolicyBuffer(self.gamma))

        self.policy_ls = []
        self.value_ls=[]

        self.lr_policy=0.001
        self.lr_value=0.001
        self.entropy_coef=0.01

        self.optimizer_policy_ls=[] #= optim.Adam(self.actor_net.parameters(), lr = self.lr_policy)    # 策略网络优化器
        self.optimizer_value_ls=[] #= optim.Adam(self.critic_net.parameters(), lr = self.lr_value) # 价值网络优化器

        #self.scheduler_policy_ls=[]
        #self.scheduler_value_ls=[]

        for i in range(self.n_agent):
            policyNet=Ma2cPolicyNet(n_s_ls[i],n_a_ls[i]).apply(init_weights)
            valueNet=Ma2cValueNet(n_s_ls[i]).apply(init_weights)
            self.policy_ls.append(policyNet)
            self.value_ls.append(valueNet)

            self.optimizer_policy_ls.append(optim.Adam(policyNet.parameters(), lr = self.lr_policy))
            self.optimizer_value_ls.append(optim.Adam(valueNet.parameters(), lr = self.lr_value))
            #self.scheduler_policy_ls.append( StepLR(self.optimizer_policy_ls[i], step_size=20, gamma=0.9))
            #self.scheduler_value_ls.append( StepLR(self.optimizer_value_ls[i], step_size=20, gamma=0.9))

    def resetLstm(self):
        for i in range(self.n_agent):
            self.value_ls[i].resetLstm()
            self.policy_ls[i].resetLstm()
            self.trans_buffer_ls[i].reset()

    def init_weights(m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0, std=0.1)

    def learn(self,v):
        #print("learn")

        for i in range(self.n_agent):
            #print("sample_transition")
            #print(i)
            obs, acts, Rs, Advs = self.trans_buffer_ls[i].sample_transition(v[i])

            # if i==0:
            #     #print(obs)
            #     print("return")
            #     print(acts)
            #     print(Rs)
            #     print(Advs)

            obs = torch.tensor(obs, dtype=torch.float)
            value_net=self.value_ls[i]
            vs=value_net(obs)

            Rs=torch.Tensor(Rs)
            Rs=Rs.view(-1,1)
            value_loss_fn=torch.nn.MSELoss()
            value_loss=value_loss_fn(vs,Rs)

            # if i==0:
            #     print(Rs)
            #     print(vs)

            policy_net=self.policy_ls[i]
            pi=policy_net(obs)

            log_pi=torch.log(pi)
            acts=torch.tensor(acts)
            acts=acts.long()
            Advs=torch.tensor(Advs)
            n_a=self.n_a_ls[i]
            #print(acts)
            acts = F.one_hot(acts, n_a)

            # if i==1:
            #     print("===")
            #     print(acts)
            #     print(log_pi)
            #     print(Advs)
            #     print((acts*log_pi).sum(dim=1))
            #     print((((acts*log_pi).sum(dim=1))*Advs))

            policy_loss_1=(((acts*log_pi).sum(dim=1))*Advs).mean()
            entropy_loss=((pi*log_pi).sum(dim=1)).mean()*self.entropy_coef

            policy_loss=policy_loss_1+entropy_loss

            #policy_loss = policy_loss_1

            # if i==0:
            # print(i)
            # print(value_loss)
            # print(policy_loss)


            optimizer_policy=self.optimizer_policy_ls[i]
            optimizer_policy.zero_grad()
            #policy_loss.backward(retain_graph=True)
            policy_loss.backward()
            nn.utils.clip_grad_norm_(policy_net.parameters(), 0.5)
            optimizer_policy.step()
            #self.scheduler_policy_ls[i].step()

            optimizer_value=self.optimizer_value_ls[i]
            optimizer_value.zero_grad()
            #value_loss.backward(retain_graph=True)
            value_loss.backward()
            nn.utils.clip_grad_norm_(value_net.parameters(),0.5)

            optimizer_value.step()
            #self.scheduler_value_ls[i].step()



    def forward(self,ob):
        value=[]
        for i in range(self.n_agent):
            value.append(i)
        return value,value

    # just forward one step for all
    def policy_net_forward(self,ob):
        #print(ob)
        policy=[]
        for i in range(self.n_agent):
            net=self.policy_ls[i]
            o=ob[i]
            o=torch.tensor(o,dtype=torch.float)
            o=o.view(1,-1)
            out=net(o)
            #print(out)
            outList=out.tolist()[0]

            outList = np.array(outList)
            outList/=outList.sum()
            outList=outList.tolist()
            policy.append(outList)
            #print(outList)

        return policy


    # just forward one step for all
    def value_net_forward(self,ob):
        value=[]
        for i in range(self.n_agent):
            net=self.value_ls[i]
            o=ob[i]
            o=torch.tensor(o,dtype=torch.float)
            o=o.view(1,-1)
            out=net(o)
            value.append(out.item())
        return value


    def add_transition(self,ob, action, reward, value, done):
        reward=np.array(reward)
        # reward_clip=4
        # reward_norm=20
        # reward = reward / reward_norm
        # reward = np.clip(reward, -reward_clip, reward_clip)

        for i in range(self.n_agent):
            self.trans_buffer_ls[i].add_transition(ob[i], action[i],reward[i], value[i], done)

    def saveModel(self,name,run):
        for i in range(self.n_agent):
            policy_net=self.policy_ls[i]
            value_net=self.value_ls[i]
            path='../result/output/{}/{}_{}/'.format(self.sorted_nodes[i],name,run)
            if not os.path.exists(path):
                os.makedirs(path)
            # torch.save({'model': policy_net.state_dict()}, path+'policy.pth')
            # torch.save({'model': value_net.state_dict()}, path+'value.pth')
            torch.save(policy_net, path+'policy.pt')
            torch.save(value_net, path+'value.pt')



    def loadModel(self,policyPath,valuePath):
        for i in range(self.n_agent):
            # policy_dict = torch.load(policyPath[i])
            # self.policy_ls[i].load_state_dict(policy_dict['model'])
            # value_dict = torch.load(valuePath[i])
            # self.value_ls[i].load_state_dict(value_dict['model'])
            self.policy_ls[i]=torch.load(policyPath[i])
            self.value_ls[i]=torch.load(valuePath[i])







