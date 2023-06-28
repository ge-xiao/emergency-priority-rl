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
        self.phase_duration=25
        self.yellow_interval_sec=2
        self.ilds_in=[]
        self.sim=sim
        self.neighbor=neighbor
        self.n_a=len(phases)

        self.EVs = list()
        self.ev_waitTimes = dict()
        self.total_ev=set()
        self.last_action_EVs = []

        self.since_last=0
        self.cur_action=0

        self.isYellow = False
        self.yellowTime = 0

        self.sim.trafficlight.setRedYellowGreenState(self.name, self.phases[0])

        self.vehicle_size_min_gap = 7.5

        self.hasEV = False
        self.ev = -1

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


    def _get_node_phase(self,action):
        prev_action=self.prev_action
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



    def get_emergency_lane(self):
        lanes = self.ilds_in
        # print(self.name)
        # print(lanes)

        for laneIdx in range(len(lanes)):
            lane = lanes[laneIdx]
            IDs = self.sim.lanearea.getLastStepVehicleIDs(lane)

            for i in range(len(IDs)):
                vc = IDs[i]
                if vc.find("emergency") != -1:
                    return vc,lane
        return None,None


    def getNewAction(self,lane):
        for idx in range(len(self.lanes_in)):
            if lane==self.lanes_in[idx]:
                for i in range(len(self.phases)):
                    phase=self.phases[i]
                    if phase[idx]=='g' or phase[idx]=='G':
                        return i


    def updataEV(self):
        lanes = self.ilds_in
        self.EVs=[]

        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            # if lane=='p_1_0-t_1_1_0':
            #     print(lane)
            #     print(self.sim.lanearea.getLastStepVehicleIDs(lane))

            IDs = self.sim.lanearea.getLastStepVehicleIDs(lane)

            for i in range(len(IDs)):
                vc = IDs[i]
                if vc.find("emergency") != -1:
                    self.EVs.append(vc)

                    self.total_ev.add(vc)

        #print(self.total_ev)
        for ev in self.total_ev.copy():
            try:
                delay = self.sim.vehicle.getAccumulatedWaitingTime(ev)
                self.ev_waitTimes.update({ev: delay})
            except:
                self.total_ev.remove(ev)



    def updatePhase(self):
        self.since_last+=1
        self.updataEV()


        if self.isYellow:
            self.yellowTime+=1
            if self.yellowTime>=self.yellow_interval_sec:
                self.isYellow=False
                new_phase = self.phases[self.cur_action]
                self.sim.trafficlight.setRedYellowGreenState(self.name, new_phase)


        if self.hasEV:
            IDs = self.sim.lanearea.getLastStepVehicleIDs(self.emergency_lane)
            if self.ev not in IDs:
                self.hasEV=False
                self.prev_action = self.cur_action
                self.cur_action = (self.cur_action + 1) % len(self.phases)

                new_phase = self._get_node_phase(self.cur_action)
                self.sim.trafficlight.setRedYellowGreenState(self.name, new_phase)
                self.isYellow = True
                self.yellowTime = 0
                self.since_last = 0

        else:

            ev,emergency_lane=self.get_emergency_lane()


            if emergency_lane is not None:
                ev_action=self.getNewAction(emergency_lane)


                if self.cur_action!=ev_action:

                    self.prev_action = self.cur_action
                    self.cur_action = ev_action

                    new_phase = self._get_node_phase(self.cur_action)
                    self.sim.trafficlight.setRedYellowGreenState(self.name, new_phase)
                    self.isYellow = True
                    self.yellowTime = 0
                    self.since_last = 0

                self.hasEV=True
                self.ev=ev
                self.emergency_lane=emergency_lane
                self.since_last = 0



            if self.since_last>=self.phase_duration:

                self.prev_action=self.cur_action
                self.cur_action=(self.cur_action+1)%len(self.phases)

                new_phase=self._get_node_phase(self.cur_action)
                self.sim.trafficlight.setRedYellowGreenState(self.name, new_phase)
                self.isYellow=True
                self.yellowTime=0
                self.since_last=0




class TrafficSimulator:
    def __init__(self,config):
        self.config=config
        self.trafficInfo={}
        with open(config.get('trafficInfo_file'), encoding='utf-8') as a:
            self.trafficInfo = json.load(a)


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
                phases=self.trafficInfo['node_phases'][node_name]
            else:
                phases = self.trafficInfo['phases']
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
        command += ['--seed', str(self.seed)]
        print(self.seed)

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

        if self.num_ev > 0:
            command += ['--tripinfo-output', output_path + ('evaluate_%s_%s_trip.xml' % (str(self.num_ev), self.seed))]
        else:
            command += ['--tripinfo-output', output_path + ('evaluate_%s_trip.xml' % (self.seed))]

        subprocess.Popen(command)

        # wait 2s to establish the traci server
        time.sleep(0.2)
        self.sim = traci.connect(port=self.port)



    def _simulate(self):

        self.sim.simulationStep()
        self.cur_sec += 1
        #print(self.cur_sec)

        #self._measure_traffic_step()
        # for node_name in self.sorted_nodes:
        #     node = self.nodes[node_name]
        #     node.updataEV()
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
                self.env.saveResult("priority_"+str(self.num_ev), seed)
            else:
                self.env.saveResult("priority", seed)


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('../config/test_5x5/priority.ini')
    #config.read('../config/test_5x5_2/priority.ini')
    #config.read('../config/hangzhou/priority.ini')
    #config.read('../config/manhattan/priority.ini')

    env=TrafficSimulator(config['ENV_CONFIG'])

    evaluate=Evaluate(env)
    #evaluate=Evaluate(env,1)

    evaluate.test()


