import numpy as np
import pandas as pd
import subprocess
from sumolib import checkBinary
import time
import traci
import json
import os
from environment.node import Node

class TrafficSimulator:
    def __init__(self,config,mode="train"):
        self.config=config
        self.trafficInfo={}
        with open(config.get('trafficInfo_file'), encoding='utf-8') as a:
            self.trafficInfo = json.load(a)

        self.train_seed = config.getint('train_seed')
        self.seed=self.train_seed
        self.port=config.getint('port')
        if mode=="tester":
            self.port = config.getint('tester_port')
        if mode=="evaluate":
            self.port = config.getint('evaluate_port')

        self.control_interval_sec = config.getint('control_interval_sec')
        self.yellow_interval_sec = config.getint('yellow_interval_sec')
        self.episode_length_sec = config.getint('episode_length_sec')
        self.coop_gamma=config.getfloat('coop_gamma')

        self.cur_sec=0
        self.cur_episode = -1
        self.n_a_ls=[]
        self.n_s_ls=[]
        self.traffic_data=[]
        self.control_data=[]
        self.trip_data = []
        self.mode=mode
        self.hasPrune=False
        self.tot_lane_hasev=[]
        self.interact_time=0

        self.neighbor_map=self.trafficInfo['neighbor_map']
        self.tot_neighbor_map=self.trafficInfo['tot_neighbor_map']

        self._init_sim()
        self._init_nodes(self.sim)

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            self.tot_lane_hasev.append([0 for lane in node.ilds_in] )
        #print(self.tot_lane_hasev)

        self.get_state()

        self._init_space()
        self.terminate()



    def _init_nodes(self,sim):
        nodes = {}
        phases = self.trafficInfo['phases']

        for node_name in self.sim.trafficlight.getIDList():
            #print(node_name)
            neighbor=[]
            tot_neighbor=[]

            if node_name in self.neighbor_map:
                neighbor = self.neighbor_map[node_name]
                tot_neighbor=self.tot_neighbor_map[node_name]

            nodes[node_name] = Node(node_name,phases,sim,neighbor,tot_neighbor)

        self.sorted_nodes = sorted(list(nodes.keys()))
        self.nodes=nodes


    def _init_space(self):
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            self.n_a_ls.append(node.n_a)
            self.n_s_ls.append(node.n_s)



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


    def _simulate(self, num_step):
        # reward = np.zeros(len(self.control_node_names))
        for _ in range(num_step):
            self.sim.simulationStep()
            # self._measure_state_step()
            # reward += self._measure_reward_step()
            self.cur_sec += 1
            #print("step:"+str(self.cur_sec))
            self._measure_traffic_step()
            for node_name in self.sorted_nodes:
                node = self.nodes[node_name]
                node.updataEV()
            # if self.is_record:
            #     # self._debug_traffic_step()
            #     self._measure_traffic_step()
        # return reward




    def get_state(self):
        state=[]

        node_idx=0
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            phase_id, posArray, speedArray, density, queue=node.get_node_state()

            # if node_name == "t_1_1":
            #     print(node_name)
            #     print(wait_lanes)
                #print(posArray)
                #print(speedArray)
                #print(node.ilds_in)
                #print(node.findIndex)


            lane_hasev = [0 for lane in node.ilds_in]

            comm_node=set()
            if self.hasPrune:
                node_lane_hasev = self.tot_lane_hasev[node_idx]

                for i in range(len(node_lane_hasev)):
                    if node_lane_hasev[i]==1:
                        str=node.ilds_in[i]
                        for nnode_name in node.neighbor:
                            if nnode_name in str:
                                comm_node.add(nnode_name)
                                break

                # print(node_name)
                # print(node_lane_hasev)
                # print(node.ilds_in)
                # print(comm_node)


            for nnode_name in node.neighbor:

                if (self.hasPrune==False) or (nnode_name in comm_node):
                    self.interact_time+=1
                    tup = self.nodes[nnode_name].hasEVComing(node_name)

                    if tup != None:
                        (ev_coming_lane, ev) = tup
                        idx = node.ilds_in.index(ev_coming_lane)
                        lane_hasev[idx]=1


            # for nnode_name in node.neighbor:
            #
            #     tup = self.nodes[nnode_name].hasEVComing(node_name)
            #     if tup != None:
            #         (ev_coming_lane, ev) = tup
            #         idx = node.findIndex[ev_coming_lane]
            #         posArray[idx] += self.coop_gamma
            #         speedArray[idx] += (self.sim.vehicle.getSpeed(ev) / node.norm_speed) * self.coop_gamma

            # if node_name == "t_2_1":
            #     print("after")
            #     print(lane_hasev)

            node_lane_hasev=self.tot_lane_hasev[node_idx]
            for i in range(len(node_lane_hasev)):
                node_lane_hasev[i]=node_lane_hasev[i]|lane_hasev[i]

            # print(node_name)
            # print(node.ilds_in)
            # print(lane_hasev)
            cur_state = phase_id + posArray + speedArray + density + queue + lane_hasev
            node.n_s = len(cur_state)

            # for nnode_name in node.neighbor:
            #     a=self.nodes[nnode_name].prev_action
            #     if a==-1:
            #         res=[0 for i in range(self.nodes[nnode_name].n_a)]
            #     else:
            #         a = torch.tensor(a)
            #         a=a.long()
            #         a = F.one_hot(a, self.nodes[nnode_name].n_a)*self.coop_gamma
            #
            #         res=a.tolist()
            #     cur_state +=res
            #     #cur_state+=self.nodes[nnode_name].fingerprint
            # node.n_s=len(cur_state)


            # for nnode_name in node.neighbor:
            #     if self.nodes[nnode_name].hasEV()==1:
            #         cur_state.append(1)
            #     else:
            #         cur_state.append(0)
            # node.n_s=len(cur_state)

            state.append(np.array(cur_state))


        # new_state = []
        # for node_name, s in zip(self.sorted_nodes, state):
        #     node = self.nodes[node_name]
        #
        #     cur_state = s
        #     for nnode_name in self.nodes[node_name].neighbor:
        #         i = self.sorted_nodes.index(nnode_name)
        #         cur_state=np.hstack((cur_state,self.coop_gamma * state[i]))
        #     new_state.append(cur_state)
        #
        #     node.n_s = len(cur_state)
            node_idx+=1

        return state

    def get_tot_lane_hasev(self):

        return self.tot_lane_hasev
    def get_interact_time(self):
        return self.interact_time

    def _measure_reward_step(self):
        reward=[]
        idx=0

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            #print(node_name)
            cur_reward=node.getReward()


            reward.append(cur_reward)

            idx+=1
            # if node_name=='t_2_2':
            #     print(node_name)
            #     print(cur_reward)
        new_reward=[]
        for node_name, r in zip(self.sorted_nodes, reward):
            cur_reward = r
            for nnode_name in self.nodes[node_name].neighbor:
                i = self.sorted_nodes.index(nnode_name)
                cur_reward += self.coop_gamma * reward[i]
            new_reward.append(cur_reward)

        global_reward = np.sum(reward) # for fair comparison
        return reward,global_reward


    def terminate(self):
        self.sim.close()



    def reset(self,mode="train",epoch=-1,tester_seed=-1,evaluate_seed=-1):
        # if self.cur_episode!=0:
        #     self.terminate()
        self.mode=mode
        self.cur_episode = epoch
        # train with false
        if mode=="test":
            self.seed=self.config.getint('test_seed')
            gui = self.config.getint('test_gui')
        elif mode=="tester":
            self.seed=tester_seed
            gui = self.config.getint('tester_gui')
        elif mode=="evaluate":
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

        return state



    def step(self,action):

        self._set_phase(action, 'yellow', self.yellow_interval_sec)
        self._simulate(self.yellow_interval_sec)
        rest_interval_sec = self.control_interval_sec - self.yellow_interval_sec
        self._set_phase(action, 'green', rest_interval_sec)
        self._simulate(rest_interval_sec)

        reward,global_reward = self._measure_reward_step()
        state = self.get_state()

        done = False


        #print(self.cur_sec)
        if self.cur_sec >= self.episode_length_sec:
            done = True

        action_r = ','.join(['%d' % a for a in action])
        cur_control = {
                       'time_sec': self.cur_sec,
                       'step': self.cur_sec / self.control_interval_sec,
                       'action': action_r,
                       'reward': global_reward}
        self.control_data.append(cur_control)

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




