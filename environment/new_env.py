import numpy as np
import pandas as pd
import subprocess
from sumolib import checkBinary
import time
import traci
import json
import os
from environment.node import Node
from agents.judge_ev_agent import Judege_ev_agent
from utils.graph import Graph
from utils.dijkstra_module import Dijkstra_module

class TrafficSimulator:
    def __init__(self,config,mode="train"):
        self.config=config
        self.trafficInfo={}
        with open(config.get('trafficInfo_file'), encoding='utf-8') as a:
            self.trafficInfo = json.load(a)

        self.train_seed = config.getint('train_seed')
        self.seed=self.train_seed
        self.port=config.getint('port')

        if "evaluate" in mode:
            self.port = config.getint('evaluate_port')

        self.control_interval_sec = config.getint('control_interval_sec')
        self.yellow_interval_sec = config.getint('yellow_interval_sec')
        self.episode_length_sec = config.getint('episode_length_sec')
        self.coop_gamma=config.getfloat('coop_gamma')

        self.train_judge_run=config.getint('train_judge_run')
        self.cur_sec=0
        self.cur_episode = -1
        self.num_ev=-1
        self.n_a_ls=[]
        self.n_s_ls=[]
        self.traffic_data=[]
        self.control_data=[]
        self.trip_data = []
        self.judge_n_s_mp = {}
        self.mode=mode

        self.neighbor_map=self.trafficInfo['neighbor_map']
        self.tot_neighbor_map=self.trafficInfo['tot_neighbor_map']
        self.sorted_nodes=self.trafficInfo['sorted_nodes']

        self._init_sim()
        self._init_nodes(self.sim)
        ###Dij
        self.dijkstra_module=Dijkstra_module(self.sim,self.trafficInfo,self.sorted_nodes)

        self.get_state()

        self._init_space()
        self.terminate()



    def _init_nodes(self,sim):
        nodes = {}


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
        #根据场上最大的ev数，指定测试的数据
        if self.num_ev>0:
            sumocfg_file = sumocfg_file.replace("exp.sumocfg", "exp_" + str(self.num_ev) + ".sumocfg")
            print(sumocfg_file)
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

        if self.num_ev>0:
            command += ['--tripinfo-output', output_path + ('%s_%s_%s_trip.xml' % (self.mode,str(self.num_ev), self.cur_episode))]
        else:
            command += ['--tripinfo-output',output_path + ('%s_%s_trip.xml' % (self.mode,self.cur_episode))]
        #print(command)

        subprocess.Popen(command)

        # wait 2s to establish the traci server
        time.sleep(0.2)
        self.sim = traci.connect(port=self.port)


    def _get_node_phase(self,action, node_name, phase_type):
        node = self.nodes[node_name]
        cur_phase = node.getPhase(action)

        if phase_type == 'green':
            return cur_phase
        prev_action = node.prev_action
        node.prev_action = action
        if (prev_action < 0) or (action == prev_action):
            return cur_phase
        prev_phase = node.getPhase(prev_action)

        switch_reds = []
        switch_greens = []
        for i, (p0, p1) in enumerate(zip(prev_phase, cur_phase)):
            if (p0 in 'Gg') and (p1 == 'r'):
                switch_reds.append(i)
            elif (p0 in 'r') and (p1 in 'Gg'):
                switch_greens.append(i)
        if not len(switch_reds):
            return cur_phase
        yellow_phase = list(cur_phase)
        for i in switch_reds:
            yellow_phase[i] = 'y'
        for i in switch_greens:
            yellow_phase[i] = 'r'
        return ''.join(yellow_phase)

    def _set_phase(self,action,phase_type,phase_duration):
        for node_name, a in zip(self.sorted_nodes, list(action)):
            phase = self._get_node_phase(a, node_name, phase_type)
            self.sim.trafficlight.setRedYellowGreenState(node_name, phase)

    def _measure_traffic_step(self):
        cars = self.sim.vehicle.getIDList()
        num_tot_car = len(cars)
        num_in_car = self.sim.simulation.getDepartedNumber()
        num_out_car = self.sim.simulation.getArrivedNumber()
        if num_tot_car > 0:
            avg_waiting_time = np.mean([self.sim.vehicle.getWaitingTime(car) for car in cars])
            avg_speed = np.mean([self.sim.vehicle.getSpeed(car) for car in cars])
        else:
            avg_speed = 0
            avg_waiting_time = 0
        # all trip-related measurements are not supported by traci,
        # need to read from outputfile afterwards
        queues = []
        for node_name in self.sorted_nodes:
            for ild in self.nodes[node_name].ilds_in:
                queues.append(self.sim.lane.getLastStepHaltingNumber(ild))
        avg_queue = np.mean(np.array(queues))
        std_queue = np.std(np.array(queues))
        cur_traffic = {
                       'time_sec': self.cur_sec,
                       'number_total_car': num_tot_car,
                       'number_departed_car': num_in_car,
                       'number_arrived_car': num_out_car,
                       'avg_wait_sec': avg_waiting_time,
                       'avg_speed_mps': avg_speed,
                       'std_queue': std_queue,
                       'avg_queue': avg_queue}
        self.traffic_data.append(cur_traffic)

    def run_judge(self):
        state={}

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            if node.time_to_act():
                if node_name not in state:
                    state[node_name] = {}
                state[node_name] = node.getJudgeState()

        actions = {}
        for ts in state.keys():
            s = state[ts]
            actions[ts] = {ev: self.judge_agents[ts].act(s[ev]) for ev in s.keys()}
            #print(ts)
            #print(actions[ts])

        for ts, action in actions.items():
            if self.nodes[ts].time_to_act():
                self.nodes[ts].apply_action(action)


    def _simulate(self, num_step):
        for _ in range(num_step):
            self.sim.simulationStep()
            self.cur_sec += 1

            ###Dij
            self.dijkstra_module.run()

            if "combine" in self.mode and self.cur_sec%2==0:
                for ts in self.sorted_nodes:
                    self.nodes[ts].detectNewEV()
                    self.nodes[ts].recordRoute()
                    self.run_judge()
                    self.get_reward()


            #self._measure_traffic_step()



    def get_state(self):
        state=[]

        cur_state_mp={}

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            phase_id, posArray, speedArray, density, queue,lane_meanWait=node.get_node_state()


            if "combine" in self.mode:
                # 保存上一时刻的lane_hasev用于奖励
                node.update_lane_hasev()
                commInfo=node.getNextCommInfo_judge()
                # print(node_name)
                # print(commInfo)
                for to_node in commInfo.keys():
                    if to_node in self.nodes:
                        for item in commInfo[to_node]:
                            #print(node_name)
                            #print(commInfo)
                            ev=item['ev']
                            edge=item['edge']
                            lanes=item['lanes']
                            self.nodes[to_node].comingInfo[ev]={"lanes":lanes,"edge":edge,"sec":self.cur_sec}


            cur_state = phase_id + posArray + speedArray + density + queue+lane_meanWait
            cur_state_mp[node_name]=cur_state
            node.n_s = len(cur_state)


        #组装最后的state
        for node_name in self.sorted_nodes:
            # print(node_name)
            # print(lane_hasev_mp[node_name])
            node = self.nodes[node_name]
            if "combine" in self.mode:
                lane_hasev=node.get_lane_hasev(self.cur_sec)
                # print(node_name)
                # print(lane_hasev)
                cur_state=cur_state_mp[node_name]+lane_hasev
                # print(node_name)
                # print(lane_hasev)
            else:
                cur_state = cur_state_mp[node_name]
            node.n_s = len(cur_state)
            state.append(np.array(cur_state))
        # print('=======')
        return state



    def _measure_reward_step(self,action):
        reward=[]
        idx=0
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            #print(node_name)
            cur_reward=node.getReward(action[idx])
            reward.append(cur_reward)
            # if node_name=='t_2_4':
            #     print(cur_reward)
            idx+=1
            # if node_name=='t_2_2':
            #     print(node_name)
            #     print(cur_reward)

        global_reward = np.sum(reward) # for fair comparison
        return reward,global_reward



    def terminate(self):
        self.sim.close()


    def reset(self,mode="train",epoch=-1,evaluate_seed=-1,num_ev=-1):
        # if self.cur_episode!=0:
        #     self.terminate()
        self.num_ev=num_ev
        if "combine" in mode:
            # 初始化判断的智能体
            self.judge_agents = {ts: Judege_ev_agent(n_actions=self.nodes[ts].n_judge_a, n_features=self.judge_n_s_mp[ts], agent_name=ts) for
                                 ts in self.sorted_nodes}
            for ts in self.sorted_nodes:
                path = '../result_judge/output/{}/{}_{}/judge.pt'.format(ts, "train_judge", self.train_judge_run)
                self.judge_agents[ts].loadModel(path)


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
            self._init_sim(gui=True)
        else:
            self._init_sim()

        self._init_nodes(self.sim)
        state=self.get_state()
        self._init_space()
        #print(state)
        self.cur_sec = 0
        self.traffic_data=[]
        ###Dij
        self.dijkstra_module.reset(self.sim)

        return state



    def step(self,action):
        # print("cur sec")
        # print(self.cur_sec)
        # print("take action")
        # print(action)
        self._set_phase(action, 'yellow', self.yellow_interval_sec)
        self._simulate(self.yellow_interval_sec)
        rest_interval_sec = self.control_interval_sec - self.yellow_interval_sec
        self._set_phase(action, 'green', rest_interval_sec)
        self._simulate(rest_interval_sec)

        state = self.get_state()
        reward,global_reward = self._measure_reward_step(action)

        # print(self.sorted_nodes)
        # print(reward[5])

        done = False

        if self.cur_sec >= self.episode_length_sec:
            done = True

        # control_data太大
        # action_r = ','.join(['%d' % a for a in action])
        # cur_control = {
        #                'time_sec': self.cur_sec,
        #                'step': self.cur_sec / self.control_interval_sec,
        #                'action': action_r,
        #                'reward': global_reward}
        # self.control_data.append(cur_control)
        return state, reward, done, global_reward


    def update_fingerprint(self,policy):
        for node_name, pi in zip(self.sorted_nodes, policy):
            self.nodes[node_name].fingerprint = pi[:-1]


    def saveResult(self,name,run):

        traffic_data = pd.DataFrame(self.traffic_data)
        #output_path='../result/output/{}_{}/'.format(name,run)
        output_path = '../result/output/traffic/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        traffic_data.to_csv(output_path + ('%s_%s_traffic.csv' % (name, run)),index=False)

        control_data = pd.DataFrame(self.control_data)
        #output_path='../result/output/{}_{}/'.format(name,run)
        output_path = '../result/output/control/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        control_data.to_csv(output_path + ('%s_%s_control.csv' % (name, run)),index=False)


    def get_reward(self):
        rewards={}
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            rewards[node_name]=node.getJudgeReward()
        return rewards

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
        self.covers_data = []


        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            if self.getMpMean(node.ev_cover)!="":
                covers.append(self.getMpMean(node.ev_cover))

            if self.getMpMean(node.ev_waste)!="":
                wastes.append(self.getMpMean(node.ev_waste))

        self.covers_data.append({"epoch":run,"cover":np.array(covers).mean(),"waste":np.array(wastes).mean()})

        output_path = '../result/output/judge/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        covers_data=pd.DataFrame(self.covers_data)
        covers_data.to_csv(output_path + ('%s_%s_cover.csv' % (name, run)), index=False)

