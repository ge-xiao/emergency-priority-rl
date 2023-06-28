import numpy as np
import pandas as pd
import subprocess
from sumolib import checkBinary
import time
import traci
import json
import os
from environment.node import Node
from utils.graph import Graph
from utils.dijkstra_module import Dijkstra_module


class judge_ev_TrafficSimulator:
    def __init__(self,config,config_model,mode="train"):
        self.config=config
        self.trafficInfo={}
        with open(config.get('trafficInfo_file'), encoding='utf-8') as a:
            self.trafficInfo = json.load(a)

        self.train_seed = config.getint('train_seed')
        self.seed=self.train_seed
        self.port=config.getint('port')

        if mode=="evaluate":
            self.port = config.getint('evaluate_port')

        self.episode_length_sec = config.getint('episode_length_sec')
        self.cur_sec=0
        self.cur_episode = -1
        self.n_a_ls=[]
        self.n_s_ls=[]

        self.mode=mode

        self.neighbor_map=self.trafficInfo['neighbor_map']
        self.tot_neighbor_map=self.trafficInfo['tot_neighbor_map']
        self.outEdges=self.trafficInfo['outEdges']
        self.sorted_nodes=self.trafficInfo['sorted_nodes']

        self.covers_data = []


        self._init_sim()
        self._init_nodes(self.sim)
        ###Dij
        self.dijkstra_module=Dijkstra_module(self.sim,self.trafficInfo,self.sorted_nodes)

        self.get_state()
        self._init_space()
        self.terminate()


    def _init_nodes(self,sim):
        nodes = {}

        #print(self.sorted_nodes)
        for node_name in self.sorted_nodes:
            #print(node_name)
            neighbor=[]
            tot_neighbor=[]
            if node_name in self.neighbor_map:
                neighbor = self.neighbor_map[node_name]
                tot_neighbor=self.tot_neighbor_map[node_name]

            if 'node_phases' in self.trafficInfo:
                phases=self.trafficInfo['node_phases'][node_name]
            else:
                phases = self.trafficInfo['phases']
            nodes[node_name] = Node(node_name,self.mode,phases,sim,neighbor,tot_neighbor)


        self.nodes=nodes




    def _init_space(self):
        self.judge_n_s_mp={}
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            self.n_a_ls.append(node.n_a)
            self.n_s_ls.append(node.n_s)
            self.judge_n_s_mp[node_name]=node.judge_n_s



    def _init_sim(self, gui=False):
        sumocfg_file = self.config.get('sumocfg_file')

        if gui:
            app = 'sumo-gui'
        else:
            app = 'sumo'
        #app = 'sumo-gui'

        command = [checkBinary(app), '-c', sumocfg_file]
        command += ['--seed', str(self.seed)]
        command += ['--remote-port', str(self.port)]
        command += ['--no-step-log', 'True']

        command += ['--time-to-teleport', '300']
        command += ['--no-warnings', 'True']
        command += ['--duration-log.disable', 'True']

        if app == 'sumo-gui':
            #sumo_cmd.extend(['--start', '--quit-on-end'])
            command+=[ '--quit-on-end']
        # collect trip info if necessary
        output_path = '../result/output/trip/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)


        #command += ['--tripinfo-output',output_path + ('%s_%s_trip.xml' % (self.mode,self.cur_episode))]
        #print(command)

        subprocess.Popen(command)

        # wait 2s to establish the traci server
        time.sleep(0.2)
        self.sim = traci.connect(port=self.port)


    def _simulate(self, num_step):

        for _ in range(num_step):
            self.sim.simulationStep()
            self.cur_sec += 1
            #print(self.cur_sec)
            #print(self.sim.simulation.getTime())
            #print("step:"+str(self.cur_sec))

            ###Dij
            self.dijkstra_module.run()


    def terminate(self):
        self.sim.close()



    def reset(self,mode="train",epoch=-1,evaluate_seed=-1):
        # if self.cur_episode!=0:
        #     self.terminate()
        self.mode=mode
        self.cur_episode = epoch
        # train with false
        if "test" in  mode:
            self.seed=self.config.getint('test_seed')
            gui = self.config.getint('test_gui')
        elif "evaluate" in mode:
            self.seed=evaluate_seed
            gui = self.config.getint('evaluate_gui')
        else:
            self.train_seed+=1
            self.seed=self.train_seed
            gui=self.config.getint('gui')

        if gui==1 :
            self._init_sim(True)
        else:
            self._init_sim()

        self._init_nodes(self.sim)
        state=self.get_state()
        self._init_space()
        #print(state)
        self.cur_sec = 0
        self.interact_time=0
        self.traffic_data=[]
        ###Dij
        self.dijkstra_module.reset(self.sim)

        return state


    def _run_steps(self):
        time_to_act = False
        while not time_to_act:
            self._simulate(2)

            for node_name in self.sorted_nodes:
                node = self.nodes[node_name]
                node.detectNewEV()
                node.recordRoute()


            if self.cur_sec >= self.episode_length_sec:
                break
            for ts in self.sorted_nodes:
                #print(ts)
                #print(self.nodes[ts].hasJudgedEV_route)
                #print(self.nodes[ts].hasJudgedEV)
                #self.nodes[ts].update()
                if self.nodes[ts].time_to_act():
                    time_to_act = True


    def _apply_actions(self, actions):
        # print("_apply_actions")
        # print(actions)

        for ts, action in actions.items():
            if self.nodes[ts].time_to_act():
                self.nodes[ts].apply_action(action)


    def step(self,action):

        self._apply_actions(action)
        self._run_steps()

        reward = self._compute_rewards()
        state = self.get_state()
        info={}
        done = False

        #print(self.cur_sec)
        if self.cur_sec >= self.episode_length_sec:
            done = True

        return state, reward, done,info


    def _compute_rewards(self):
        reward={}

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]

            #cur_reward=node.getJudgeReward()
            cur_reward=0
            reward[node_name]=cur_reward

        return reward


    def get_state(self):
        state={}

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            if node.time_to_act():
                if node_name not in state:
                    state[node_name] = {}
                    #print(state[node_name])
                #print(node_name)
                state[node_name] = node.getJudgeState()

        return state

    def get_reward(self):
        rewards={}
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            rewards[node_name]=node.getJudgeReward()
        return rewards


    def get_route(self,node_name):
        route=self.nodes[node_name].hasJudgedEV_route
        print(route)


    def getMpMean(self,mp):

        ls = []
        for k in mp.keys():
            ls.append(mp[k])
        if len(ls)==0:
            return ""
        return np.array(ls).mean()

    def save_judge_result(self,name,run):
        covers=[]
        wastes=[]

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            if self.getMpMean(node.ev_cover)!="":
                covers.append(self.getMpMean(node.ev_cover))

            if self.getMpMean(node.ev_waste)!="":
                wastes.append(self.getMpMean(node.ev_waste))

        self.covers_data.append({"epoch":run,"cover":np.array(covers).mean(),"waste":np.array(wastes).mean()})

        output_path = '../result_judge/output/judge/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        covers_data=pd.DataFrame(self.covers_data)
        covers_data.to_csv(output_path + ('%s_%s_cover.csv' % (name, run)), index=False)


            # print(node_name)
            # print(node.ev_cover)
            # print(node.ev_waste)


