import numpy as np
import pandas as pd
import subprocess
from sumolib import checkBinary
import time
import traci
import json
import os
import configparser
from utils.dijkstra_module import Dijkstra_module


class Node:
    def __init__(self, name,phases,sim,neighbor):

        self.emergency_lane = None
        self.name = name
        self.prev_action=0
        self.phases=phases
        self.phase_duration=30
        self.yellow_interval_sec=2
        self.ilds_in=[]
        self.sim=sim
        self.neighbor=neighbor
        self.n_a=len(phases)


        self.since_last=0
        self.cur_action=0
        self.isYellow = False
        self.yellowTime = 0

        self.sim.trafficlight.setRedYellowGreenState(self.name, self.phases[0])

        self.vehicle_size_min_gap = 7.5

        lanes_in = self.sim.trafficlight.getControlledLanes(name)
        self.lanes_in=lanes_in

        ilds_in = []
        for lane_name in lanes_in:
            ild_name = lane_name
            if ild_name not in ilds_in:
                ilds_in.append(ild_name)
        # nodes[node_name].edges_in = edges_in
        self.ilds_in = ilds_in

        self.lanes_length = {lane: self.sim.lane.getLength(lane) for lane in self.ilds_in}

        self.IDs_mp = {lane: [] for lane in self.ilds_in}
        self.EVs=[]

        self.init_ETLSA()

    def init_ETLSA(self):

        plan = self.getPlan()
        self.plan=plan
        self.cur_stage=0
        self.cur_duration=plan[self.cur_stage][1]
        self.cur_action=plan[self.cur_stage][0]

        # if self.name=='t_1_5':
        #     plan=self.getPlan()
        #     # print(plan)
        self.sim.trafficlight.setRedYellowGreenState(self.name, self.phases[self.cur_action])


    def _get_node_phase(self,prev_action,action):

        cur_phase=self.phases[action]
        prev_phase = self.phases[prev_action]

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


    #得到最佳绿灯时间
    def getBestGreen(self,lane):

        IDs = self.IDs_mp[lane]
        ans=0
        for i in range(len(IDs)):
            vc = IDs[i]
            pos = self.sim.vehicle.getLanePosition(vc)

            length=self.lanes_length[lane]
            toCenter = int(length - pos)
            if toCenter > ans:
                ans = toCenter
        return min(28.0,ans/6)

    def updataEV(self):
        self.EVs=[]
        lanes = self.ilds_in
        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            IDs = self.sim.lane.getLastStepVehicleIDs(lane)
            self.IDs_mp[lane]=IDs
            for vc in IDs:
                if "emergency" in vc:
                    if self.sim.vehicle.getLaneID(vc).find(":")!=-1:
                        continue
                    self.EVs.append(vc)

    def getPhasesIdx(self,ev_lane):
        lanes_in=self.lanes_in

        for i in range(len(self.phases)):
            phase=self.phases[i]
            for idx in range(len(phase)):
                if 'G' in phase[idx] or 'g' in phase[idx]:
                    if lanes_in[idx]== ev_lane:
                        return i


    def getPlan(self):
        plan = []

        lanes_in=self.lanes_in
        sums=[0 for i in range(self.n_a)]
        best_green=[0 for i in range(self.n_a)]

        for i in range(len(self.phases)):
            phase=self.phases[i]
            n_sum=0
            bg=0
            lanes=[]
            for idx in range(len(phase)):
                if 'G' in phase[idx] or 'g' in phase[idx]:
                    if lanes_in[idx] not in lanes:
                        lanes.append(lanes_in[idx])

            for lane in lanes:
                n_sum+=self.sim.lane.getLastStepVehicleNumber(lane)
                bg=max(bg,self.getBestGreen(lane))

            sums[i]=n_sum
            best_green[i]=bg

        # if self.name=='t_0':
        #     print(sums)

        for t in range(self.n_a):
            maxIndex=-1
            maxValue=-1

            #优先安排包含特车的流量。
            if len(self.EVs)>0:
                vc=self.EVs[0]
                ev_lane=self.sim.vehicle.getLaneID(vc)
                self.EVs.remove(vc)

                maxIndex=self.getPhasesIdx(ev_lane)

                #print("安排",maxIndex)
            else:
                #选出当前最大的sum的下标
                for j in range(self.n_a):
                    if sums[j]>maxValue:
                        maxValue=sums[j]
                        maxIndex=j

            sums[maxIndex]=-1
            plan.append((maxIndex,best_green[maxIndex]))

        # if self.name=='t_0':
        #     print(plan)
        return plan


    def updatePhase(self):
        self.since_last += 1

        if self.isYellow:
            self.yellowTime+=1
            if self.yellowTime>=self.yellow_interval_sec:
                self.isYellow=False
                new_phase = self.phases[self.cur_action]
                self.sim.trafficlight.setRedYellowGreenState(self.name, new_phase)


        if self.since_last>=self.cur_duration:
            self.prev_action=self.cur_action
            #计算plan中的下一阶段，当最后一个阶段时，计算新的Plan
            self.cur_stage+=1
            if self.cur_stage>=self.n_a:
                self.cur_stage=0
                self.plan=self.getPlan()
                # if self.name == 't_1_5':
                #     print(self.plan)

            self.cur_duration = self.plan[self.cur_stage][1]
            self.cur_action = self.plan[self.cur_stage][0]

            #是否要安排黄灯
            if self.prev_action==self.cur_action:
                self.isYellow = False
            else:
                self.isYellow = True
                self.yellowTime = 0

            #新的相位
            new_phase=self._get_node_phase(self.prev_action,self.cur_action)
            self.sim.trafficlight.setRedYellowGreenState(self.name, new_phase)
            self.since_last=0



class TrafficSimulator:
    def __init__(self,config):
        self.config=config
        self.trafficInfo={}
        with open(config.get('trafficInfo_file'), encoding='utf-8') as a:
            self.trafficInfo = json.load(a)

        with open('../net/manhattan/ETLSA.json', encoding='utf-8') as a:
            self.ET_trafficInfo = json.load(a)
        self.seed=-1
        self.port=config.getint('port')
        self.yellow_interval_sec = config.getint('yellow_interval_sec')
        self.episode_length_sec = config.getint('episode_length_sec')

        self.cur_sec=0
        self.cur_episode = -1
        self.num_ev = -1

        self.traffic_data=[]
        self.trip_data = []

        self.neighbor_map=self.trafficInfo['neighbor_map']
        self.tot_neighbor_map=self.trafficInfo['tot_neighbor_map']
        self.sorted_nodes=self.trafficInfo['sorted_nodes']

        self._init_sim()
        self._init_nodes(self.sim)

        ###Dij
        self.dijkstra_module=Dijkstra_module(self.sim,self.trafficInfo,self.sorted_nodes)



    def _init_nodes(self,sim):
        nodes = {}


        for node_name in self.sim.trafficlight.getIDList():
            #print(node_name)
            neighbor=[]
            if node_name in self.neighbor_map:
                neighbor = self.neighbor_map[node_name]

            if 'node_phases' in self.trafficInfo:
                phases=self.ET_trafficInfo['node_phases'][node_name]
            else:

                phases = self.ET_trafficInfo['phases']


            nodes[node_name] = Node(node_name,phases,sim,neighbor)


        self.nodes=nodes



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
        print(self.seed)
        command += ['--seed', str(self.seed)]
        command += ['--remote-port', str(self.port)]
        command += ['--no-step-log', 'True']

        command += ['--time-to-teleport', '300']
        command += ['--no-warnings', 'True']
        command += ['--duration-log.disable', 'True']

        if app == 'sumo-gui':
            #sumo_cmd.extend(['--start', '--quit-on-end'])
            command+=[ '--quit-on-end']
        output_path = self.config.get('output_path')+'trip/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        if self.num_ev>0:
            command += ['--tripinfo-output', output_path + ('evaluate_%s_%s_trip.xml' % (str(self.num_ev),self.seed))]
        else:
            command += ['--tripinfo-output',output_path +  ('evaluate_%s_trip.xml' % (self.seed))]
        subprocess.Popen(command)

        # wait 2s to establish the traci server
        time.sleep(0.2)
        self.sim = traci.connect(port=self.port)



    def _simulate(self):
        self.sim.simulationStep()
        self.cur_sec += 1
        #print(self.cur_sec)

        #self._measure_traffic_step()

        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            node.updataEV()

        ###Dij
        self.dijkstra_module.run()

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

    def reset(self,evaluate_seed=0,num_ev=-1):
        # if self.cur_episode!=0:
        #     self.terminate()
        self.cur_episode = evaluate_seed
        self.num_ev=num_ev

        self.seed=evaluate_seed
        gui=self.config.getint('gui')

        if gui==1 :
            self._init_sim(True)
        else:
            self._init_sim()

        self._init_nodes(self.sim)
        #print(state)
        self.cur_sec = 0
        self.traffic_data=[]

        ###Dij
        self.dijkstra_module.reset(self.sim)



    def updatePhase(self):
        for node_name in self.sorted_nodes:
            node = self.nodes[node_name]
            node.updatePhase()



    def run(self):
        while True:
            self._simulate()
            self.updatePhase()
            if self.cur_sec>=self.episode_length_sec:
                self.terminate()
                break

    def terminate(self):
        self.sim.close()

    def saveResult(self,name,run):

        traffic_data = pd.DataFrame(self.traffic_data)
        #output_path='../result/output/{}_{}/'.format(name,run)
        output_path = self.config.get('output_path')+"traffic/"
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        traffic_data.to_csv(output_path + ('%s_%s_traffic.csv' % (name, run)),index=False)



class Evaluate():
    def __init__(self, env,num_ev=-1):
        self.env=env
        self.name="evaluate"
        self.mode="evaluate"
        self.num_ev=num_ev
        self.evaluate_seed=range(10000, 100001, 10000)

    def test(self):

        for seed in self.evaluate_seed:
            if self.num_ev>0:
                self.env.reset(evaluate_seed=seed,num_ev=self.num_ev)
            else:
                self.env.reset(evaluate_seed=seed)
            self.env.run()
            if self.num_ev > 0:
                self.env.saveResult("ETLSA_"+str(self.num_ev), seed)
            else:
                self.env.saveResult("ETLSA", seed)


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('../config/manhattan/ETLSA.ini')

    env=TrafficSimulator(config['ENV_CONFIG'])

    evaluate=Evaluate(env)
    #evaluate=Evaluate(env,1)

    evaluate.test()



